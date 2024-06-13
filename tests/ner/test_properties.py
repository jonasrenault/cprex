import pytest
import spacy
from cprex.ner.properties import PROPERTY_PATTERNS


@pytest.fixture(scope="module")
def nlp():
    pipe = spacy.load("en_core_web_sm", disable=["ner"])
    ruler = pipe.add_pipe("entity_ruler", last=True)
    ruler.add_patterns(PROPERTY_PATTERNS)
    return pipe


def test_thermal(nlp):
    text = "the thermal decomposition of the sulfonic acid occurs around 292-419°C"
    doc = nlp(text)
    assert [(ent.label_, ent.text, ent.id_) for ent in doc.ents] == [
        ("PROP", "thermal decomposition", "thermal")
    ]


def test_stability(nlp):
    text = "predicted Ti3C2Tx-SO3H-5's stability until 300 °C"
    doc = nlp(text)
    assert [(ent.label_, ent.text, ent.id_) for ent in doc.ents] == [
        ("PROP", "stability until", "temperature")
    ]

    text = "MXene is stable up to 180°C"
    doc = nlp(text)
    assert [(ent.label_, ent.text, ent.id_) for ent in doc.ents] == [
        ("PROP", "stable up to", "temperature")
    ]


def test_energy(nlp):
    text = "we calculate the activation energy (ΔG) of benzene"
    doc = nlp(text)
    assert [(ent.label_, ent.text, ent.id_) for ent in doc.ents] == [
        ("PROP", "activation energy", "energy"),
        ("FORMULA", "ΔG", "energy"),
    ]

    text = (
        "The formation energy of this pentameric assembly is very large (-836.7 kcal/mol)"
    )
    doc = nlp(text)
    assert [(ent.label_, ent.text, ent.id_) for ent in doc.ents] == [
        ("PROP", "formation energy", "energy"),
    ]


# def test_ph(nlp):
#     text = "the ph of Ti 3 AlC 2 was around 6-7."


def test_absorptivity(nlp):
    pass
