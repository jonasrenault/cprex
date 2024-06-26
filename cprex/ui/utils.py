import subprocess
import time
from collections import Counter
from io import BytesIO
from pathlib import Path

import requests
import streamlit as st
from spacy.tokens import Doc, Span

from cprex.commands import DEFAULT_INSTALL_DIR
from cprex.corpus.tuples import ChemPropValueRelation, extract_tuple_relations
from cprex.ner.chem_ner import ner_article
from cprex.parser.pdf_parser import Article, parse_pdf_to_dict
from cprex.pipeline import get_pipeline

GROBID_QTY_ISALIVE_URL = "http://localhost:8060/service/isalive"
GROBID_ISALIVE_URL = "http://localhost:8070/api/isalive"


@st.cache_resource
def get_nlp():
    nlp = get_pipeline(spacy_model="en_core_web_sm")

    return nlp


@st.cache_resource
def check_models():
    pubmedbert_dir = DEFAULT_INSTALL_DIR / "pubmedbert"
    if not Path(pubmedbert_dir).is_dir():
        st.error(
            "Unable to find the BERT model for Named Entity Recognition "
            "of chemical compounds. Make sure it's installed by running "
            "`cprex install-models` before starting the UI.",
            icon=":material/deployed_code_alert:",
        )

    relmodel_dir = DEFAULT_INSTALL_DIR / "rel_model"
    if not Path(relmodel_dir).is_dir():
        st.error(
            "Unable to find the Relation Extraction model. Make sure it's installed "
            "by running `cprex install-models` before starting the UI.",
            icon=":material/deployed_code_alert:",
        )


def check_grobid(service: str, url: str, display_error: bool):
    try:
        r = requests.get(url)
        r.raise_for_status()
    except Exception:
        if display_error:
            st.error(
                f"Unable to connect to the {service} service. Make sure it's running "
                "by running `cprex start-grobid` before starting the UI.",
                icon=":material/chat_error:",
            )
        return False
    return True


@st.cache_resource
def check_start_grobid():
    procs = []
    # Check or start grobid
    grobid_service = (
        DEFAULT_INSTALL_DIR / "grobid" / "grobid-service" / "bin" / "grobid-service"
    )
    grobid_is_running = check_grobid(
        "grobid", GROBID_ISALIVE_URL, not grobid_service.exists()
    )
    if not grobid_is_running and grobid_service.exists():
        procs.append(
            subprocess.Popen([str(grobid_service)], cwd=DEFAULT_INSTALL_DIR / "grobid")
        )

    # Check or start grobid-quantity
    grobid_qty_service = (
        DEFAULT_INSTALL_DIR / "grobid" / "grobid-quantities" / "bin" / "grobid-quantities"
    )
    grobid_qty_is_running = check_grobid(
        "grobid-quantities", GROBID_QTY_ISALIVE_URL, not grobid_qty_service.exists()
    )
    if not grobid_qty_is_running and grobid_qty_service.exists():
        procs.append(
            subprocess.Popen(
                [
                    str(grobid_qty_service),
                    "server",
                    str(
                        DEFAULT_INSTALL_DIR
                        / "grobid"
                        / "grobid-quantities"
                        / "resources"
                        / "config"
                        / "config.yml"
                    ),
                ]
            )
        )

    if len(procs) > 0:
        with st.spinner("Grobid services are starting..."):
            time.sleep(10)

    return procs


@st.cache_data
def process_pdf(pdf: bytes, segment_sentences: bool = False) -> Article:
    article = parse_pdf_to_dict(BytesIO(pdf), segment_sentences=segment_sentences)
    return article


@st.cache_data
def run_pipeline(article: Article) -> list[Doc]:
    nlp = get_nlp()
    docs = ner_article(article, nlp)
    return docs


@st.cache_data
def get_pdf_content_from_url(pdf_url: str) -> bytes:
    headers = requests.utils.default_headers()
    headers["User-Agent"] = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko)"
        " Chrome/56.0.2924.87 Safari/537.36"
    )
    with st.spinner("Downloading file..."):
        r = requests.get(pdf_url, headers=headers)
    return r.content


def get_html(html: str) -> str:
    """Convert HTML so it can be rendered."""
    WRAPPER = """<div style="overflow-x: auto;
    margin-bottom: 1rem">{}</div>"""
    # Newlines seem to mess with the rendering
    html = html.replace("\n", " ")
    return WRAPPER.format(html)


def display_entity_values(counts: Counter, color: str, label: str, height: int = 200):
    with st.container(height=height):
        st.write(
            f"<span style='color: {color}; font-weight: bold;'>{label}</span>"
            f"<span style='float:right; font-weight: bold;'>{counts.total()}</span>",
            unsafe_allow_html=True,
        )
        values = "".join(
            [
                f"{key} <span style='float:right'>{value}</span><br>"
                for key, value in counts.most_common()
            ]
        )
        st.markdown(values, unsafe_allow_html=True)


def format_entity_value(chem: Span, color: str):
    return (
        f"<span style='background-color: {color}; padding: 0.25em;"
        "border-radius: 0.5em;display:inline-block;"
        f"margin: .25em .25em 0;'>{chem.text}</span>"
    )


def display_relation(rel: ChemPropValueRelation):
    tags = []
    if rel.chemicals is not None:
        for chem in rel.chemicals:
            tags.append(format_entity_value(chem, "pink"))
    if rel.properties is not None:
        for prop in rel.properties:
            tags.append(format_entity_value(prop, "#feca74"))
    tags.append(format_entity_value(rel.value, "#7aecec"))

    with st.container(border=True):
        st.write("".join(tags), unsafe_allow_html=True)


def get_relations(
    docs: list[Doc], triplets_only: bool = False
) -> list[ChemPropValueRelation]:
    res = []
    for doc in docs:
        tuples = extract_tuple_relations(doc)
        for tuple_ in tuples:
            if tuple_.chemicals is not None and (
                not triplets_only or tuple_.properties is not None
            ):
                res.append(tuple_)

    return res


def count_entities(docs: list[Doc]) -> tuple[Counter, Counter, Counter]:
    chems = []
    props = []
    qtys = []
    for doc in docs:
        for ent in doc.ents:
            if ent.label_ == "CHEM":
                chems.append(ent.text)
            elif ent.label_ == "PROP":
                props.append(ent.ent_id_)
            else:
                qtys.append(ent.label_)

    return Counter(chems), Counter(props), Counter(qtys)
