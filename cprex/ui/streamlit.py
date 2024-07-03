from typing import Any

import streamlit as st
from spacy.tokens import Doc

from cprex.displacy.render import render
from cprex.parser.pdf_parser import Article
from cprex.ui.utils import (
    check_grobid,
    check_models,
    count_entities,
    display_entity_information,
    display_entity_values,
    display_relation,
    get_html,
    get_pdf_content_from_url,
    get_relations,
    link_entities,
    process_pdf,
    run_pipeline,
)

# Define session state and callbacks for file submission
if "url_submited" not in st.session_state:
    st.session_state.url_submited = False
if "file_uploaded" not in st.session_state:
    st.session_state.file_uploaded = False


def on_submit_local_file():
    st.session_state.file_uploaded = True
    st.session_state.url_submited = False
    st.session_state.selected_entity = None


def on_submit_remote_file():
    st.session_state.url_submited = True
    st.session_state.file_uploaded = False
    st.session_state.selected_entity = None


# Set page title
st.set_page_config(
    page_title="CPREx - Chemical Properties Relation Extraction",
    # page_icon="👋",
)

# Set some custom style
st.markdown(
    """<style>
    div[data-testid="stSidebarContent"]
    div[data-testid="stVerticalBlockBorderWrapper"]
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: white;
    }

    div[data-testid="stSidebarContent"]
    div[data-testid="stVerticalBlockBorderWrapper"]
    div[data-testid="stVerticalBlockBorderWrapper"]
    div[data-testid="stVerticalBlockBorderWrapper"]
    div[data-testid="stVerticalBlock"] {
        gap: .1rem;
    }

    div[data-testid="stSidebarContent"]
    div[data-testid="stVerticalBlockBorderWrapper"]
    div[data-testid="stVerticalBlockBorderWrapper"]
    div[data-testid="stVerticalBlockBorderWrapper"]
    div[data-testid="stVerticalBlock"]
    button[kind="secondary"] {
        padding: 0;
        justify-content: normal;
        border: 0;
        color: #0468c9;
        background-color: transparent;
        min-height: 1.5rem;
    }
    </style>""",
    unsafe_allow_html=True,
)

st.title("CPREx - Chemical Properties Relation Extraction")
st.markdown(
    """
    CPREx is a NLP pipeline for automatic extraction of chemical
    compounds and their properties from scientific text.

    It uses Named Entity Recognition (NER) models to detect entities of interest,
    and a custom trained Relation Extraction (RE) model to detect relations
    between those entities and form tuples of chemical entities and their
    properties expressed in the text.""",
    unsafe_allow_html=True,
)

with st.expander("How to use it"):
    st.write(
        """
        **Instructions:**
        1. Upload a PDF file of a scientic publication (preferably
        in the field of chemistry)
        2. Wait for the pipeline to process the article!
        3. The text annotated with named entities will display below;
        the properties and values linked to a chemical compound will
        display in the left sidebar."""
    )


uploaded_file = st.file_uploader(
    "Choose a file to upload", type="pdf", on_change=on_submit_local_file
)

pdf_url = st.text_input(
    "Or enter the URL of a PDF file and press Submit",
    "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10343900/pdf/molecules-28-05029.pdf",
)

st.button("Submit !", on_click=on_submit_remote_file)

###############################
### Make sure models are downloaded and grobid is running.
### These functions are cached with st, so should only run once
### on startup
###############################
check_models()
check_grobid()


def display_article(article: Article, docs: list[Doc]):
    st.subheader(article.title)
    st.markdown(
        f"**:blue[{article.pub_date}]** "
        f"<span style='float:right'>**:blue[{article.doi}]**</span>",
        unsafe_allow_html=True,
    )
    if article.authors is not None:
        st.caption(", ".join(article.authors))

    previous_title = None
    for doc in docs:
        if previous_title != doc._.section and doc._.section != "":
            st.divider()
            st.markdown(f"**{doc._.section}**")
            previous_title = doc._.section

        html = render(doc)
        st.write(get_html(html), unsafe_allow_html=True)


def display_filters(
    docs: list[Doc],
    relations: list[dict[str, Any]],
    properties: dict[str, dict[str, Any]],
):
    chems, props, qtys = count_entities(docs)
    with st.sidebar:
        st.markdown("**Entities**")
        st.caption(
            "Linked entities are displayed in blue. "
            "Click on one to display information extracted from PubChem."
        )
        display_entity_values(chems, "pink", "Chemicals", properties=properties)
        if (
            "selected_entity" in st.session_state
            and st.session_state.selected_entity is not None
        ):
            display_entity_information(properties)
        display_entity_values(props, "#feca74", "Properties")
        display_entity_values(qtys, "#7aecec", "Values")

        st.markdown("**Relations**")
        for rel in relations:
            display_relation(rel)


def parse_pdf_and_display_results(pdf: bytes, segment_sentences: bool = False):
    try:
        with st.spinner("Your file is being processed..."):
            article = process_pdf(pdf, segment_sentences)
            docs = run_pipeline(article)
            relations = get_relations(tuple(docs))
            properties = link_entities(tuple(docs))

        display_article(article, docs)
        display_filters(docs, relations, properties)
    except Exception as e:
        st.warning(
            """
            🚨 An error occured while processing the file. Check the filetype & file
            format and try again ...
            """
        )
        raise e


if st.session_state.file_uploaded and uploaded_file is not None:
    parse_pdf_and_display_results(uploaded_file.getvalue())
elif st.session_state.url_submited and pdf_url:
    parse_pdf_and_display_results(get_pdf_content_from_url(pdf_url))
else:
    st.stop()
