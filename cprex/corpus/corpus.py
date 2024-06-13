import json
import logging
import traceback
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

from spacy.language import Language
from spacy.tokens import Doc, DocBin
from tqdm import tqdm

from cprex.crawler.chemrxiv import (
    ChemrxivAPI,
    download_pdf_for_paper,
    parse_article_metadata,
)
from cprex.ner.chem_ner import ner_article
from cprex.ner.quantities import PROPERTY_TO_UNITS
from cprex.parser.pdf_parser import parse_pdf_to_dict

logger = logging.getLogger(__name__)


@dataclass
class ParsedPaper:
    title: str
    doi: str
    id: str
    docs: list[Doc]


def prop_matches_quantity(doc: Doc) -> bool:
    """
    Checks that the doc has a property entity and a quantity
    entity with valid unit.
    i.e if the doc has an enthalpy property, return true if
    the doc also has a quantity with an enthalpy unit.

    Args:
        doc (Doc): the doc to check

    Returns:
        bool: True if doc has property and corresponding quantity
    """
    prop_types = [ent.ent_id_ for ent in doc.ents]
    quantity_types = [ent.label_ for ent in doc.ents]

    for property, units in PROPERTY_TO_UNITS.items():
        if property in prop_types and (
            (len(units) == 0 and len(quantity_types) > 0)
            or any([unit in quantity_types for unit in units])
        ):
            return True

    return False


def filter_doc(doc: Doc) -> bool:
    """
    Filter a doc to check that we should keep it, i.e.
    that it contains a property and a quantity.

    Args:
        doc (Doc): the doc to check

    Returns:
        bool: True if we should keep the doc
    """
    return prop_matches_quantity(doc)


def parse_and_filter_pdf(
    pdf: str | Path | BytesIO, nlp: Language, segment_sentences=False, filter: bool = True
) -> list[Doc]:
    """
    Parse the pdf file with the nlp pipeline and filter the resulting docs
    to only keep those interesting (with property and quantity entities).

    Args:
        pdf (Path): the path to the pdf file
        nlp (Language): the spacy nlp pipeline
        segment_sentences (bool, optional): whether to segment sentences
        during parsing. Defaults to False.
        filter (bool, optional): whether to filter docs. Defaults to True.

    Returns:
        list[Doc]: the filtered docs
    """
    article = parse_pdf_to_dict(pdf, segment_sentences=segment_sentences)
    docs = ner_article(article, nlp)
    if filter:
        docs = [doc for doc in docs if filter_doc(doc)]
    return docs


def save_docs(docs: list[Doc], save_file: Path, save_trf_data: bool = False):
    """
    Save a list of docs to disk.

    Args:
        docs (list[Doc]): the list of docs to save
        save_file (Path): the path to a file where the docs will be saved
    """
    doc_bin = DocBin(store_user_data=True)
    for doc in docs:
        if not save_trf_data and Doc.has_extension("trf_data"):
            doc._.trf_data = None
        doc_bin.add(doc)

    doc_bin.to_disk(save_file)


def load_docs(save_file: Path, nlp: Language, set_doi: bool = False) -> list[Doc]:
    """
    Load a list of docs from disk.

    Args:
        save_file (Path): the file to load from
        nlp (Language): the nlp pipeline used to create the docs
        set_doi (bool, optional): update doc doi from filename. Defaults to False.

    Returns:
        list[Doc]: the list of docs loaded from the file
    """
    doc_bin = DocBin().from_disk(save_file)
    docs = list(doc_bin.get_docs(nlp.vocab))

    # set doi for docs if not present
    if set_doi:
        doi = save_file.stem.replace("_", "/")
        for doc in docs:
            doc._.doi = doi
    return docs


def crawl_chemrxiv_papers(dump_file: Path, query: str):
    """
    Crawl ChemRxiv for papers matching the search query
    and save results to a file.

    Args:
        dump_file (Path): the output file
        query (str): the search query
    """
    api = ChemrxivAPI()

    dump = []
    count = 0

    logger.info("Starting to crawl chemRxiv API.")
    for paper in tqdm(api.query_generator(f"items?term={query}")):
        dump.append(parse_article_metadata(paper["item"]))
        count += 1

    logger.info(f"Crawl finished. Dumping results to {dump_file.name}")
    with open(dump_file, "w") as f:
        for paper in dump:
            f.write(json.dumps(paper) + "\n")


def parse_papers(
    metadata_file: Path,
    download_dir: Path,
    nlp: Language,
    limit: int = 1000,
    force: bool = False,
    save_parsed_docs: bool = False,
) -> list[ParsedPaper]:
    """
    Given a metadata_file containing a list of paper metadata (title, doi, pdf_url),
    download the PDFs and process them with the given nlp pipeline.

    Args:
        metadata_file (Path): metadata_file with list of papers to process.
        download_dir (Path): directory where PDF files are saved.
        nlp (Language): the spacy pipeline used to process papers
        limit (int, optional): limit of papers to process. Defaults to 1000.
        force (bool, optional): if true, process all papers, otherwise process
            only new papers. Defaults to False.
        save_parsed_docs (bool, optional): if ture, save parsed docs to disk.
            Defaults to False.

    Returns:
        list[ParsedPaper]: list of ParsedPaper
    """
    # get list of papers from metadata file
    logger.info("Reading paper metadata ...")
    with open(metadata_file, "r") as f:
        papers = [json.loads(line) for line in f.readlines()]
    if force:
        for paper in papers:
            if "processed" in paper:
                del paper["processed"]

    # process articles
    output: list[ParsedPaper] = []
    logger.info(f"Processing papers (max {limit}) ...")
    for paper in tqdm([p for p in papers if "pdf" in p and "processed" not in p][:limit]):
        try:
            pdf_file = download_dir / f"{paper['doi'].replace('/', '_')}.pdf"
            if not pdf_file.exists():
                download_pdf_for_paper(paper["pdf"], pdf_file)

            docs = parse_and_filter_pdf(pdf_file, nlp, segment_sentences=False)
            output.append(ParsedPaper(paper["title"], paper["doi"], paper["id"], docs))

            if save_parsed_docs and docs:
                save_docs(docs, download_dir / f"{paper['doi'].replace('/', '_')}.spacy")
        except Exception as e:
            logger.error(e)
            traceback.print_exc()
        finally:
            paper["processed"] = True

    logger.info("Done processing. Writing output.")
    with open(metadata_file, "w") as f:
        for paper in papers:
            f.write(json.dumps(paper) + "\n")

    return output


def export_doc_to_label_studio(doc: Doc) -> dict[str, Any]:
    """
    Export a doc to label-studio format.
    See https://labelstud.io/guide/predictions#Import-span-pre-annotations-for-text
    and https://labelstud.io/guide/tasks#Basic-Label-Studio-JSON-format
    for details on label-studio format.

    Args:
        doc (Doc): the doc

    Returns:
        dict[str, Any]: the data in label-studio format
    """
    predictions = []
    for ent in doc.ents:
        pred = {
            "from_name": "label",
            "to_name": "text",
            "type": "labels",
            "value": {
                "start": ent.start_char,
                "end": ent.end_char,
                "text": str(ent.text),
                "labels": [
                    (
                        str(ent.label_)
                        if ent.label_ in ("CHEM", "PROP", "FORMULA")
                        else "VALUE"
                    )
                ],
            },
        }
        predictions.append(pred)
    output = {"data": {"text": doc.text}, "predictions": [{"result": predictions}]}
    return output
