import logging
import warnings
from pathlib import Path

import click

warnings.filterwarnings("ignore", category=UserWarning)
from cprex.corpus.corpus import crawl_chemrxiv_papers, parse_papers  # noqa: E402
from cprex.displacy.render import render_docs  # noqa: E402
from cprex.pipeline import get_pipeline  # noqa: E402

CPREX_HOME_DIR = Path.home() / ".cprex"
DEFAULT_DOWNLOAD_DIR = CPREX_HOME_DIR / "data"

logger = logging.getLogger("cprex.corpus.corpus")
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(ch)


@click.group()
def main():
    pass


@main.command()
@click.option(
    "-d",
    "--download-dir",
    "download_dir",
    help="directory where the data (PDFs, DocBins) will be saved",
    default=DEFAULT_DOWNLOAD_DIR,
    type=click.Path(dir_okay=True),
)
@click.option(
    "-l",
    "--limit",
    "limit",
    help="Max number of papers to parse",
    default=100,
    type=click.INT,
)
@click.option(
    "-s",
    "--save-docs",
    "save_docs",
    help="save parsed docs as spacy DocBins",
    default=False,
    is_flag=True,
)
@click.argument("query")
def create_corpus(download_dir: str, limit: int, save_docs: bool, query: str) -> None:
    # First crawl ChemRxiv for metadata
    papers_metadata = CPREX_HOME_DIR / f"{query}_papers.jsonl"
    if papers_metadata.exists():
        click.echo(
            f"Query metadata file {papers_metadata} already exists. Not crawling again."
        )
    else:
        crawl_chemrxiv_papers(papers_metadata, query)

    # Build pipeline
    nlp = get_pipeline(spacy_model="en_core_web_sm")

    # Create download_dir if it does not exist
    save_dir = Path(download_dir)
    save_dir.mkdir(exist_ok=True)

    # Parse papers
    parsed_papers = parse_papers(
        papers_metadata, save_dir, nlp, limit=limit, save_parsed_docs=save_docs
    )

    # Visualise
    for paper in parsed_papers:
        if paper.docs:
            print(paper.title)
            render_docs(paper.docs, jupyter=False)


if __name__ == "__main__":
    main()
