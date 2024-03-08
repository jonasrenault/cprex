from pathlib import Path

import spacy
from spacy.language import Language
from spacy.tokens import Doc

# These imports are required for Spacy to be able to load
# the custom components
from cprex.ner.abbreviations import AbbreviationDetector  # noqa: F401
from cprex.ner.chem_ner import create_chem_ner_component  # noqa: F401
from cprex.ner.properties import PROPERTY_PATTERNS
from cprex.ner.quantities import create_quantities_ner_component  # noqa: F401
from cprex.rel.rel_model import (
    create_classification_layer,  # noqa: F401
    create_instances,  # noqa: F401
    create_relation_model,  # noqa: F401
    create_tensors,  # noqa: F401
)
from cprex.rel.rel_pipe import make_relation_extractor  # noqa: F401

DEFAULT_MODEL_DIR = Path.home() / ".cprex"


def get_pipeline(
    bert_model_directory: str = f"{DEFAULT_MODEL_DIR}/pubmedbert",
    spacy_model: str = "en_core_web_sm",
    rel_model_directory: str = f"{DEFAULT_MODEL_DIR}/rel_model",
    enable_ner_pipelines: bool = True,
    enable_rel_pipeline: bool = True,
    detect_abbreviations: bool = False,
) -> Language:
    """
    Build an nlp pipeline for chemical properties extraction.
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
            last=True,
            config={"bert_model_directory": bert_model_directory},
        )

        # Add a custom component for Quantities NER
        nlp.add_pipe("add_quantities", "QuantitiesNER", after="ChemNER")

        # Add a custom entity ruler for Property NER
        ruler = nlp.add_pipe("entity_ruler", after="QuantitiesNER")
        ruler.add_patterns(PROPERTY_PATTERNS)  # type: ignore

    if detect_abbreviations:
        nlp.add_pipe("abbreviation_detector")

    # Add custom attributes to Doc class
    if not Doc.has_extension("title"):
        Doc.set_extension("title", default=None)
    if not Doc.has_extension("doi"):
        Doc.set_extension("doi", default=None)
    if not Doc.has_extension("section"):
        Doc.set_extension("section", default=None)
    if not Doc.has_extension("rel"):
        Doc.set_extension("rel", default={})

    if enable_rel_pipeline:
        rel_model = spacy.load(rel_model_directory)
        # relation_extractor = nlp.get_pipe("relation_extractor")
        nlp.add_pipe("transformer", source=rel_model)
        nlp.add_pipe("relation_extractor", source=rel_model)

    return nlp
