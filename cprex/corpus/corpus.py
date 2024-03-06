import json
import traceback
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
from cprex.ner.chem_ner import get_ner_pipeline, ner_article
from cprex.parser.pdf_parser import parse_pdf_to_dict

INTERESTING_UNITS = [
    "TEMPERATURE",
    "DENSITY",
    "ENTHALPY",
    "SOLUBILITY",
    "MOLAR VOLUME",
    "ABSORPTIVITY",
    "ENERGY",
    "VELOCITY",
    "PRESSURE",
    "HEAT CAPACITY",
    "DYNAMIC VISCOSITY",
    "THERMAL CONDUCTIVITY",
]

PROPERTY_TO_UNITS: dict[str, list[str]] = {
    "enthalpy": ["ENTHALPY"],
    "energy": ["ENERGY", "ENTHALPY"],
    "absorptivity": ["ABSORPTIVITY"],
    "heat capacity": ["HEAT CAPACITY"],
    "temperature": ["TEMPERATURE"],
    "pressure": ["PRESSURE"],
    "density": ["SOLUBILITY", "DENSITY"],
    "viscosity": ["DYNAMIC VISCOSITY"],
    "velocity": ["VELOCITY"],
    "toxicity": [],
    "thermal": ["TIME", "TEMPERATURE"],
    "formula weight": [],
    "sensibility": [],
}


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
            len(units) == 0 or any([unit in quantity_types for unit in units])
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


def parse_and_filter(pdf: Path, nlp: Language, segment_sentences=False) -> list[Doc]:
    """
    Parse the pdf file with the nlp pipeline and filter the resulting docs
    to only keep those interesting (with property and quantity entities).

    Args:
        pdf (Path): the path to the pdf file
        nlp (Language): the spacy nlp pipeline
        segment_sentences (bool, optional): whether to segment sentences
        during parsing. Defaults to False.

    Returns:
        list[Doc]: the filtered docs
    """
    article = parse_pdf_to_dict(str(pdf), segment_sentences=segment_sentences)
    docs = ner_article(article, nlp)
    filtered_docs = [doc for doc in docs if filter_doc(doc)]
    return filtered_docs


def save_docs(docs: list[Doc], save_file: Path):
    """
    Save a list of docs to disk.

    Args:
        docs (list[Doc]): the list of docs to save
        save_file (Path): the path to a file where the docs will be saved
    """
    doc_bin = DocBin(store_user_data=True)
    for doc in docs:
        doc_bin.add(doc)

    doc_bin.to_disk(save_file)


def load_docs(save_file: Path, nlp: Language) -> list[Doc]:
    """
    Load a list of docs from disk.

    Args:
        save_file (Path): the file to load from
        nlp (Language): the nlp pipeline used to create the docs

    Returns:
        list[Doc]: the list of docs loaded from the file
    """
    doc_bin = DocBin().from_disk(save_file)
    docs = list(doc_bin.get_docs(nlp.vocab))
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

    print("Starting to crawl chemRxiv API.")
    for paper in tqdm(api.query_generator(f"items?term={query}")):
        dump.append(parse_article_metadata(paper["item"]))
        count += 1

    print(f"Crawl finished. Dumping results to {dump_file.name}")
    with open(dump_file, "w") as f:
        for paper in dump:
            f.write(json.dumps(paper) + "\n")


def create_corpus_from_metadata_file(
    metadata_file: Path,
    download_dir: Path,
    limit: int = 1000,
    force: bool = False,
) -> list[Doc]:
    """
    Create a list of filtered docs from a metadata_file containing
    a list of article metadata crawled from chemrxiv.

    Args:
        metadata_file (Path): the path to the metadata file
        download_dir (Path): the dir to save the pdf files to
        limit (int, optional): the maximum number of articles to parse. Defaults to 1000.
        force (bool, optional): if True, start over from the start of the metadata
        file. Defaults to False.

    Returns:
        list[Doc]: the filtered docs
    """
    # get list of articles from metadata file
    print("Reading paper metadata")
    with open(metadata_file, "r") as f:
        papers = [json.loads(line) for line in tqdm(f.readlines())]
    if force:
        for paper in papers:
            if "processed" in paper:
                del paper["processed"]

    # create ner pipeline
    model_dir = Path() / "model"
    nlp = get_ner_pipeline(str(model_dir))

    # process articles
    count = 0
    corpus_docs = []
    try:
        for paper in tqdm(papers):
            if "pdf" in paper and "processed" not in paper:
                pdf_file = download_dir / f"{paper['doi'].replace('/', '_')}.pdf"
                if not pdf_file.exists():
                    download_pdf_for_paper(paper["pdf"], pdf_file)

                print(f"Processing {pdf_file.name}")
                docs = parse_and_filter(pdf_file, nlp, segment_sentences=False)
                corpus_docs.extend(docs)
                paper["processed"] = True
                count += 1
                if count > limit:
                    break
    except Exception as e:
        print(e)
        traceback.print_exc()
    finally:
        print("Done processing. Writing output.")
        with open(metadata_file, "w") as f:
            for paper in papers:
                f.write(json.dumps(paper) + "\n")
        return corpus_docs


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
