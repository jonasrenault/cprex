import logging
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup, NavigableString, Tag

logger = logging.getLogger(__name__)

GROBID_URL = "http://localhost:8070"


@dataclass
class Section(object):
    heading: str | None
    text: list[list[str]] | None


@dataclass
class Table(object):
    heading: str | None
    description: list[list[str]] | None
    data: pd.DataFrame | None


@dataclass
class Article(object):
    doi: str | None
    title: str | None
    authors: list[str] | None
    pub_date: str | None
    abstract: list[list[str]] | None
    sections: list[Section] | None
    tables: list[Table] | None


def parse_pdf(
    pdf_path: str | Path | BytesIO,
    grobid_url: str = GROBID_URL,
    segment_sentences: bool = False,
) -> BeautifulSoup | None:
    """
    Parse a pdf using a GROBID server.

    Parameters
    ----------
    pdf_path : str
        path of the pdf file to parse
    grobid_url : str, optional
        the GROBID server url, by default GROBID_URL
    segment_sentences : bool, optional
        if true, return each sentence separatly, by default False

    Returns
    -------
    Union[BeautifulSoup, None]
        A BeautifulSoup XML representation of the parsed article
    """
    url = f"{grobid_url}/api/processFulltextDocument"
    data = {"consolidateHeader": 1}
    if segment_sentences:
        data["segmentSentences"] = 1

    if isinstance(pdf_path, (str, Path)):
        with open(pdf_path, "rb") as f:
            r = requests.post(url, files={"input": f}, data=data, timeout=180)
    else:
        r = requests.post(url, files={"input": pdf_path}, data=data, timeout=180)
    parsed_article_text = r.text

    if parsed_article_text is not None:
        parsed_article = BeautifulSoup(parsed_article_text, "lxml-xml")
    return parsed_article


def parse_authors(article: BeautifulSoup) -> list[str]:
    """
    Parse authors from a given BeautifulSoup of an article
    """
    authors: list[str] = []
    source = article.find("sourceDesc")
    if source is None:
        return authors
    author_names = source.find_all("persName")
    for author in author_names:
        firstname = author.find("forename", {"type": "first"})
        firstname = firstname.text.strip() if firstname is not None else ""
        middlename = author.find("forename", {"type": "middle"})
        middlename = middlename.text.strip() if middlename is not None else ""
        lastname = author.find("surname")
        lastname = lastname.text.strip() if lastname is not None else ""
        if middlename != "":
            authors.append(firstname + " " + middlename + " " + lastname)
        else:
            authors.append(firstname + " " + lastname)
    return authors


def parse_date(article: BeautifulSoup) -> str:
    """
    Parse date from a given BeautifulSoup of an article
    """
    pub_date = article.find("publicationStmt")
    if pub_date is None:
        return ""
    year_tag = pub_date.find("date")
    year = year_tag.attrs.get("when") if year_tag is not None else ""
    return year


def parse_text(text: str) -> str:
    return text.replace(" \u00c0", "-").replace(" \u00bc", "=")


def parse_paragraph(p: Tag) -> list[str]:
    return [
        (
            parse_text(elem.text)
            if not isinstance(elem, NavigableString)
            else parse_text(str(elem))
        )
        for elem in p.children
    ]


def parse_abstract(article: BeautifulSoup) -> list[list[str]]:
    """
    Parse abstract from a given BeautifulSoup of an article
    """
    try:
        abstract = article.find("abstract")
        div = abstract.find("div", attrs={"xmlns": "http://www.tei-c.org/ns/1.0"})
        return [
            parse_paragraph(p)
            for p in list(div.children)
            if isinstance(p, Tag) and len(list(p)) > 0
        ]
    except AttributeError:
        return []


def parse_sections(article: BeautifulSoup) -> list[Section]:
    """
    Parse sections from a given BeautifulSoup of an article
    """
    article_text = article.find("text")
    sections = []
    if article_text is not None:
        divs = article_text.find_all(
            "div", attrs={"xmlns": "http://www.tei-c.org/ns/1.0"}
        )
        for div in divs:
            head = div.find("head")
            heading = head.text if head is not None else ""

            text = [
                parse_paragraph(p)
                for p in div.find_all("p")
                if isinstance(p, Tag) and len(list(p)) > 0
            ]

            if heading != "" or len(text) > 0:
                sections.append(Section(heading, text))

    return sections


def parse_tables(article: BeautifulSoup) -> list[Table]:
    """
    Parse tables from a given BeautifulSoup of an article
    """
    articles_tables = article.find_all("figure", {"type": "table"})
    tables = []
    for table in articles_tables:
        head = table.find("head")
        heading = head.text if head is not None else ""

        desc = table.find("figDesc")
        description = [
            parse_paragraph(p)
            for p in desc.find_all("p")
            if isinstance(p, Tag) and len(list(p)) > 0
        ]

        data = parse_table(table)
        tables.append(Table(heading, description, data))

    return tables


def parse_table(table: BeautifulSoup) -> pd.DataFrame:
    """
    Try to parse a TEI XML table into a pandas DataFrame.

    Parameters
    ----------
    table : BeautifulSoup
        the input xml table

    Returns
    -------
    pd.DataFrame
        the parsed dataframe
    """
    rows = table.find_all("row")
    table_data = []
    for row in rows:
        idx = 0
        row_data = {}
        cells = row.find_all("cell")
        for cell in cells:
            row_data[f"c_{idx}"] = parse_text(cell.text)
            if cell.get("cols") is not None:
                idx += int(cell.get("cols"))
            else:
                idx += 1
        table_data.append(row_data)

    df = pd.DataFrame.from_records(table_data)
    return df


def convert_article_soup_to_dict(
    article: BeautifulSoup,
) -> Article:
    """
    Convert an article parsed as BeautifulSoup to JSON Format.
    Output JSON is similar to the output from https://github.com/allenai/science-parse/
    """
    title = article.find("title", attrs={"type": "main"})
    title = title.text.strip() if title is not None else ""

    authors = parse_authors(article)
    pub_date = parse_date(article)
    abstract = parse_abstract(article)
    sections = parse_sections(article)
    tables = parse_tables(article)

    doi = article.find("idno", attrs={"type": "DOI"})
    doi = doi.text if doi is not None else ""

    return Article(doi, title, authors, pub_date, abstract, sections, tables)


def join_paragraphs(section: Section):
    """
    Utility method to join sentences in a section's paragraph.
    """
    if section.text is not None:
        section.text = [["".join(p)] for p in section.text]


def parse_pdf_to_dict(
    pdf_path: str | Path | BytesIO,
    grobid_url: str = GROBID_URL,
    segment_sentences: bool = True,
) -> Article:
    parsed_article = parse_pdf(
        pdf_path, grobid_url=grobid_url, segment_sentences=segment_sentences
    )
    article = convert_article_soup_to_dict(parsed_article)
    if not segment_sentences and article.sections:
        for section in article.sections:
            join_paragraphs(section)
    return article
