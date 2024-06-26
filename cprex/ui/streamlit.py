import streamlit as st
from spacy.tokens import Doc

from cprex.displacy.render import render
from cprex.parser.pdf_parser import Article
from cprex.ui.utils import (
    check_models,
    check_start_grobid,
    count_entities,
    display_entity_values,
    display_relation,
    get_html,
    get_pdf_content_from_url,
    get_relations,
    process_pdf,
    run_pipeline,
)

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
    "Choose a file to upload",
    type="pdf",
)

pdf_url = st.text_input(
    "Or enter the URL of a PDF file and press Submit",
    "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10343900/pdf/molecules-28-05029.pdf",
)

submit = st.button("Submit !")

###############################
### Make sure models are downloaded and grobid is running.
### These functions are cached with st, so should only run once
### on startup
###############################
check_models()
check_start_grobid()


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


def display_filters(docs: list[Doc]):
    chems, props, qtys = count_entities(docs)
    tuples = get_relations(docs)
    with st.sidebar:
        st.markdown("**Entities**")
        display_entity_values(chems, "pink", "Chemicals")
        display_entity_values(props, "#feca74", "Properties")
        display_entity_values(qtys, "#7aecec", "Values")

        st.markdown("**Relations**")
        for rel in tuples:
            display_relation(rel)


def parse_pdf_and_display_results(pdf: bytes, segment_sentences: bool = False):
    try:
        with st.spinner("Your file is being processed..."):
            article = process_pdf(pdf, segment_sentences)
            docs = run_pipeline(article)

        display_article(article, docs)
        display_filters(docs)
    except Exception as e:
        st.warning(
            """
            🚨 An error occured while processing the file. Check the filetype & file
            format and try again ...
            """
        )
        raise e


if uploaded_file is not None:
    parse_pdf_and_display_results(uploaded_file.getvalue())

elif submit and pdf_url:
    parse_pdf_and_display_results(get_pdf_content_from_url(pdf_url))
else:
    st.stop()
