from collections import Counter
from io import BytesIO
from pathlib import Path
from typing import Any

import requests
import streamlit as st
from spacy.tokens import Doc
from streamlit_extras.grid import grid

from cprex.commands import DEFAULT_INSTALL_DIR
from cprex.corpus.tuples import extract_tuple_relations
from cprex.ner.chem_ner import ner_article
from cprex.parser.pdf_parser import Article, parse_pdf_to_dict
from cprex.pipeline import get_pipeline
from cprex.pubchem.linker import link_compounds

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


@st.cache_resource
def check_grobid():
    grobids = {"grobid": GROBID_ISALIVE_URL, "grobid-quantities": GROBID_QTY_ISALIVE_URL}
    for service, url in grobids.items():
        try:
            r = requests.get(url)
            r.raise_for_status()
        except Exception:
            st.error(
                f"Unable to connect to the {service} service. Make sure it's running "
                "by running `cprex start-grobid` before starting the UI.",
                icon=":material/chat_error:",
            )


@st.cache_data
def process_pdf(pdf: bytes, segment_sentences: bool = False) -> Article:
    article = parse_pdf_to_dict(BytesIO(pdf), segment_sentences=segment_sentences)
    return article


@st.cache_data
def run_pipeline(article: Article) -> list[Doc]:
    nlp = get_nlp()
    docs = ner_article(article, nlp)
    return docs


@st.cache_data(hash_funcs={"spacy.tokens.doc.Doc": lambda doc: doc.to_bytes()})
def link_entities(docs: tuple[Doc]) -> dict[str, dict[str, Any]]:
    properties = link_compounds(docs, min_occurences=3)
    return properties


@st.cache_data(hash_funcs={"spacy.tokens.doc.Doc": lambda doc: doc.to_bytes()})
def get_relations(docs: tuple[Doc], triplets_only: bool = False) -> list[dict[str, Any]]:
    res = []
    for doc in docs:
        tuples = extract_tuple_relations(doc)
        for tuple_ in tuples:
            if tuple_.chemicals is not None and (
                not triplets_only or tuple_.properties is not None
            ):
                res.append(tuple_.to_dict())

    return res


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


def set_selected_entity(entity: str):
    st.session_state.selected_entity = entity


def display_entity_values(
    counts: Counter,
    color: str,
    label: str,
    height: int = 200,
    properties: dict[str, dict[str, Any]] | None = None,
):
    with st.container(height=height):
        st.write(
            f"<div><span style='color: {color}; font-weight: bold;'>{label}</span>"
            f"<span style='float:right; font-weight: bold;'>{counts.total()}</span>"
            "</div>",
            unsafe_allow_html=True,
        )
        res_grid = grid([0.9, 0.1], vertical_align="center")
        for entity, count in counts.most_common():
            if properties is not None and entity in properties:
                res_grid.button(
                    entity,
                    use_container_width=True,
                    on_click=set_selected_entity,
                    args=[entity],
                )
            else:
                res_grid.write(entity)
            res_grid.write(
                f"<span style='float:right'>{count}</span>", unsafe_allow_html=True
            )


def format_entity_value(text: str, color: str):
    return (
        f"<span style='background-color: {color}; padding: 0.25em;"
        "border-radius: 0.5em;display:inline-block;"
        f"margin: .25em .25em 0;'>{text}</span>"
    )


def display_relation(rel: dict[str, Any]):
    tags = []
    if "chemicals" in rel:
        for chem in rel["chemicals"]:
            tags.append(format_entity_value(chem["text"], "pink"))
    if "properties" in rel:
        for prop in rel["properties"]:
            tags.append(format_entity_value(prop["text"], "#feca74"))
    tags.append(format_entity_value(rel["value"]["text"], "#7aecec"))

    with st.container(border=True):
        st.write("".join(tags), unsafe_allow_html=True)


def display_entity_information(properties: dict[str, dict[str, Any]]):
    entity = st.session_state.selected_entity
    props = properties[entity]
    with st.container(height=150):
        st.markdown(f"**{entity}**")
        st.write(props)


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
