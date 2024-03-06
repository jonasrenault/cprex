from dataclasses import dataclass

import spacy
from spacy import displacy
from spacy.language import Language
from spacy.tokens import Doc, Span
from transformers import (
    AutoConfig,
    AutoModelForTokenClassification,
    AutoTokenizer,
    Pipeline,
    pipeline,
)

from cprex.ner.properties import PROPERTY_PATTERNS

# This import is required by spacy to create the quantities pipeline component
from cprex.ner.quantities import create_quantities_ner_component  # noqa: F401
from cprex.parser.pdf_parser import Article

DEFAULT_LABEL_COLORS = {
    "CHEM": "pink",
    "PROP": "#feca74",
    "FORMULA": "#c887fb",
    "TEMPERATURE": "#7aecec",
    "DENSITY": "#7aecec",
    "TIME": "#ddd",
    "PERCENT": "#ddd",
    "ENTHALPY": "#7aecec",
    "MOLAR VOLUME": "#7aecec",
    "ABSORPTIVITY": "#7aecec",
    "SOLUBILITY": "#7aecec",
    "ENERGY": "#7aecec",
    "VELOCITY": "#7aecec",
    "HEAT CAPACITY": "#7aecec",
    "THERMAL CONDUCTIVITY": "#7aecec",
    "DYNAMIC VISCOSITY": "#7aecec",
}


@dataclass
class BertEntity:
    start: int
    end: int
    label: str


def bert_to_spacy_ner_tags(ner_result, label="CHEM") -> list[BertEntity]:
    """
    Transform the results of using a bert ner pipeline on a text to a list
    of entity tags with label, start and end values.
    """
    entities = []
    for entity in ner_result:
        if entity["entity_group"] == "LABEL_0":  # B-CHEM
            entities.append(BertEntity(entity["start"], entity["end"], label))
        elif entity["entity_group"] == "LABEL_1" and entities:  # I-CHEM
            entities[-1].end = entity["end"]

    return entities


def get_token_index_from_label_positions(
    sentence: Span, start: int, end: int
) -> tuple[int | None, int | None]:
    """
    Get the token positions in a sentence,
    corresponding to a label with start and end index.
    """
    tstart = None
    tend = None
    for token in sentence:
        if (token.idx - sentence.start_char) <= start <= (
            token.idx - sentence.start_char + len(token)
        ) and tstart is None:
            tstart = token.i
        if (token.idx - sentence.start_char) >= end and tend is None:
            tend = token.i
        if tstart and tend:
            break
    if tend is None:
        tend = sentence.end
    return tstart, tend


class ChemNERComponent:
    """
    Spacy Language component for chemical NER.
    Uses a bert transformer pipeline to extract chemical entities
    then adds them to spacy's Doc.
    """

    def __init__(self, bert_model_directory: str):
        self.bert_pipeline = get_bert_pipeline(bert_model_directory)

    def __call__(self, doc: Doc):
        doc_ents = []

        # for each sentence in the document, run bert NER to extract chemical names
        for sentence in doc.sents:
            bert_entities = self.bert_pipeline(sentence.text)
            sent_entities = bert_to_spacy_ner_tags(bert_entities)

            # Add bert entities to spacy doc
            for entity in sent_entities:
                # Convert sentence start and end indices to doc token
                # start and end indices
                start, end = get_token_index_from_label_positions(
                    sentence, entity.start, entity.end
                )
                if start is not None and end is not None:
                    new_ent = Span(doc, start, end, label=entity.label)
                    doc_ents.append(new_ent)

        doc.ents = doc_ents
        return doc


@Language.factory(
    "add_chemical_entities", default_config={"bert_model_directory": "model"}
)
def create_chem_ner_component(
    nlp, name: str, bert_model_directory: str
) -> ChemNERComponent:
    return ChemNERComponent(bert_model_directory)


def get_bert_pipeline(model_directory: str) -> Pipeline:
    """
    Load the Bert Chemical Named Entity Recognizer
    from the given model directory and return it.
    """
    num_labels = 3
    config = AutoConfig.from_pretrained(
        model_directory,
        num_labels=num_labels,
        finetuning_task="ner",
        cache_dir=None,
        revision="main",
        use_auth_token=None,
    )
    tokenizer = AutoTokenizer.from_pretrained(
        model_directory,
        cache_dir=None,
        use_fast=True,
        revision="main",
        use_auth_token=None,
        model_max_length=512,
    )
    model = AutoModelForTokenClassification.from_pretrained(
        model_directory,
        from_tf=False,
        config=config,
        cache_dir=None,
        revision="main",
        use_auth_token=None,
    )

    nlp = pipeline("ner", model=model, tokenizer=tokenizer, aggregation_strategy="simple")
    return nlp


def get_ner_pipeline(
    bert_model_directory: str = "pubmedbert",
    spacy_model: str = "en_core_sci_md",
    enable_ner_pipelines: bool = True,
) -> Language:
    """
    Build an nlp pipeline for ner.
    """
    nlp = spacy.load(spacy_model, disable=["ner"])

    # Do not split sentences on abbreviations like approx.
    nlp.tokenizer.add_special_case(  # type: ignore
        "approx.", [{"ORTH": "approx.", "NORM": "approximately"}]
    )

    if enable_ner_pipelines:
        # Add a custom component for Chemical NER
        nlp.add_pipe(
            "add_chemical_entities",
            "ChemNER",
            after="parser",
            config={"bert_model_directory": bert_model_directory},
        )

        # Add a custom component for Quantities NER
        nlp.add_pipe("add_quantities", "QuantitiesNER", after="ChemNER")

        # Add a custom entity ruler for Property NER
        ruler = nlp.add_pipe("entity_ruler", after="QuantitiesNER")
        ruler.add_patterns(PROPERTY_PATTERNS)  # type: ignore

    # Add custom attributes to Doc class
    if not Doc.has_extension("title"):
        Doc.set_extension("title", default=None)
    if not Doc.has_extension("doi"):
        Doc.set_extension("doi", default=None)
    if not Doc.has_extension("section"):
        Doc.set_extension("section", default=None)
    if not Doc.has_extension("rel"):
        Doc.set_extension("rel", default={})

    return nlp


def ner_article(article: Article, nlp: Language) -> list[Doc]:
    """
    Use the given nlp spacy pipeline to process
    an article into a list of docs.

    Parameters
    ----------
    article : Article
        the article
    nlp : Language
        the pipeline

    Returns
    -------
    list[Doc]
        List of processed docs
    """
    # Build a list of text tuples (see. https://spacy.io/usage/processing-pipelines#processing)
    text_tuples: list[tuple[str, dict[str, str | None]]] = []

    if article.abstract:
        for p in article.abstract:
            for s in p:
                text_tuples.append((s, {"section": "Abstract"}))

    if article.sections:
        for section in article.sections:
            if section.text:
                for p in section.text:
                    for s in p:
                        text_tuples.append(
                            (
                                s,
                                {"section": section.heading},
                            )
                        )

    # Process texts with nlp
    docs = list(nlp.pipe(text_tuples, as_tuples=True))

    # Set custom doc context attributes
    results = []
    for doc, ctxt in docs:
        doc._.title = article.title
        doc._.doi = article.doi
        doc._.section = ctxt["section"]
        results.append(doc)
    return results


def render_ner_docs(
    docs: list[Doc],
    jupyter: bool = True,
    colors: dict[str, str] = DEFAULT_LABEL_COLORS,
):
    display_docs = []
    previous_title = None
    for doc in docs:
        doc.user_data["title"] = (
            doc._.section
            if previous_title != doc._.section and doc._.section != ""
            else None
        )
        previous_title = doc._.section
        display_docs.append(doc)

    displacy.render(
        display_docs, style="ent", jupyter=jupyter, options={"colors": colors}
    )