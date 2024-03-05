import json
import logging
import os
from datetime import timedelta
from pathlib import Path

import requests
from ratelimit import limits, sleep_and_retry  # type: ignore
from tqdm import tqdm

logger = logging.getLogger(__name__)

RATE_LIMIT_IN_SECONDS = 2
DEFAULT_PAPER_CRAWL_LIMIT = 100


class ChemrxivAPI:
    base = "https://chemrxiv.org/engage/chemrxiv/public-api/v1"

    def __init__(self, page_size: int = 50):
        self.page_size = page_size

    @sleep_and_retry
    @limits(calls=1, period=timedelta(seconds=RATE_LIMIT_IN_SECONDS).total_seconds())
    def query(self, query, params=None):
        url = os.path.join(self.base, query)
        logger.info(f"Sending request to {url}")
        r = requests.get(url, params=params, timeout=60)
        r.raise_for_status()
        return r.json()

    def query_generator(self, query, params: dict = {}):
        """Query for a list of items, with paging. Returns a generator."""

        page = 0
        while True:
            params.update({"limit": self.page_size, "skip": page * self.page_size})
            r = self.query(query, params=params)
            r = r["itemHits"]

            # If we have no more results, bail out
            if len(r) == 0:
                return

            yield from r
            page += 1

    def all_preprints(self):
        """Return a generator to all the chemRxiv articles."""
        return self.query_generator("items")

    def preprint(self, article_id):
        """Information on a given preprint."""
        return self.query(os.path.join("items", article_id))

    def number_of_preprints(self):
        return self.query("items")["totalCount"]


def parse_article_metadata(source_paper: dict) -> dict:
    """
    Select the metadata we want to save from the query response.
    """
    authors = "; ".join(
        [" ".join([a["firstName"], a["lastName"]]) for a in source_paper["authors"]]
    )

    target_paper = {
        "title": source_paper["title"],
        "doi": source_paper["doi"],
        "id": source_paper["id"],
        "abstract": source_paper["abstract"],
        "authors": authors,
    }
    if "asset" in source_paper and "original" in source_paper["asset"]:
        target_paper["pdf"] = source_paper["asset"]["original"]["url"]

    return target_paper


def download_paper_metadata(
    out_file: Path, api: ChemrxivAPI | None = None, limit: int | None = None
) -> None:
    """
    Crawl ChemRxiv for paper metadata and save it into the output file
    """
    if api is None:
        api = ChemrxivAPI()

    dump = []
    count = 0

    logger.info("Starting to crawl API.")
    for paper in tqdm(api.all_preprints()):
        dump.append(parse_article_metadata(paper["item"]))
        count += 1
        if limit and count >= limit:
            break

    logger.info(f"Crawl finished. Dumping results to {str(out_file)}")
    with open(str(out_file), "w") as f:
        for idx, target_paper in enumerate(dump):
            if idx > 0:
                f.write(os.linesep)
            f.write(json.dumps(target_paper))


@sleep_and_retry
@limits(calls=1, period=timedelta(seconds=RATE_LIMIT_IN_SECONDS).total_seconds())
def download_pdf_for_paper(url: str, out_file: Path):
    response = requests.get(url, timeout=60)
    with open(str(out_file), "wb") as pf:
        pf.write(response.content)


def download_pdfs_from_dump(dump_file: Path, save_dir: Path) -> None:
    logger.info(f"Downloading papers from dump {str(dump_file)}")

    save_dir.mkdir(exist_ok=True)

    with open(str(dump_file), "r") as f:
        for line in tqdm(f.readlines()):
            paper = json.loads(line)
            if "pdf" in paper:
                out_file = save_dir / f"{paper['doi'].replace('/', '_')}.pdf"
                if out_file.exists():
                    continue

                download_pdf_for_paper(paper["pdf"], out_file)

    logger.info(f"Done downloading files to {save_dir}")
