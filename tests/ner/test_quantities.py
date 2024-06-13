import pytest
import spacy
from cprex.ner.quantities import create_quantities_ner_component  # noqa: F401


@pytest.fixture(scope="module")
def nlp():
    pipe = spacy.load("en_core_web_sm", disable=["ner"])
    pipe.add_pipe("add_quantities", "QuantitiesNER", last=True)
    return pipe


@pytest.mark.skip(reason="neeps grobid running, and it doesn't work yet")
def test_quantities(nlp):
    text = "The formation energy of this pentameric assembly is very"
    "large (-836.7 kcal/mol) due to the pure Coulombic attraction between a "
    "tetra-anionic specie and four surrounding cations. This contribution is "
    "quite significant (-16.1 kcal/mol) due to the presence of numerous CH•••O contacts."
    "The contribution of the XBs is also indicated in Figure 8 and it is much larger "
    "( -53.4 kcal/mol ), evidencing that it is the dominant interaction. "
    "It is interesting to emphasize that for the XB CHEM in the tetragonal pyramidal "
    "arrangement, all energies are similar (ranging -2.5 to -3.6 kcal/mol), thus "
    "suggesting that the location of the I-atom in this cation is likely dominated "
    "by the nondirectional electrostatic attraction. However, in the other "
    "binding mode (four-center XBs), one XB is very strong and directional "
    "(-9.1 kcal/mol ) and the other two are much weaker ancillary XBs."
    doc = nlp(text)
    for ent in doc.ents:
        print(ent.label_, ent.text)
