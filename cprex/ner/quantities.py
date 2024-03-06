from dataclasses import dataclass

from grobid_quantities.quantities import QuantitiesAPI  # type: ignore
from spacy.language import Language
from spacy.tokens import Doc, Span


@dataclass
class GrobidEntity:
    start: int
    end: int
    label: str | None = None


def parse_grobid_measure(measure: dict, doc_text) -> GrobidEntity:
    """
    Extract start, end and label values from a measurement returned by
    the grobid-quantites API.

    See grobid-quantities doc for measurement specification
    https://grobid-quantities.readthedocs.io/en/latest/restAPI.html
    """
    if "measurementOffsets" not in measure:
        return GrobidEntity(-1, -1)

    start, end = fix_grobid_qty_offset_for_special_chars(
        doc_text,
        measure["measurementOffsets"]["start"],
        measure["measurementOffsets"]["end"],
        measure["measurementRaw"],
    )
    entity = GrobidEntity(start, end)

    # Def quantity
    quantity = {}

    if measure["type"] == "value" and "quantity" in measure:
        quantity = measure["quantity"]
    elif measure["type"] == "interval" and "quantityMost" in measure:
        quantity = measure["quantityMost"]
    elif measure["type"] == "interval" and "quantityLeast" in measure:
        quantity = measure["quantityLeast"]
    elif measure["type"] == "listc" and "quantities" in measure:
        quantity = measure["quantities"][0]

    # Extract label
    if "type" in quantity:
        entity.label = quantity["type"].upper()
    elif "rawUnit" in quantity and "type" in quantity["rawUnit"]:
        entity.label = quantity["rawUnit"]["type"].upper()
    elif "rawUnit" in quantity and "name" in quantity["rawUnit"]:
        if quantity["rawUnit"]["name"] == "%":
            entity.label = "PERCENT"
        elif quantity["rawUnit"]["name"] == "mL":
            entity.label = "VOLUME"
        elif quantity["rawUnit"]["name"] == "• C":
            entity.label = "TEMPERATURE"
        else:
            entity.label = quantity["rawUnit"]["name"].upper()

    return entity


def fix_grobid_qty_offset_for_special_chars(
    doc_text: str, start: int, end: int, raw: str
) -> tuple[int, int]:
    """
    Grobid-quantities sometimes removes special characters, which
    creates a discrepancy with spacy's doc. This function offsets
    the start and end values of grobid-quantities to account for
    missing special characters.
    """
    # offset by -1 start and end until we find the grobid-qty
    # substring
    s = start
    e = end
    while doc_text[s:e] != raw and s > 0:
        s -= 1
        e -= 1

    if doc_text[s:e] == raw:
        return s, e
    return start, end


def get_token_index_from_label_positions(
    doc: Doc, start: int, end: int
) -> tuple[int | None, int | None]:
    """
    Get the token positions in a doc,
    corresponding to a label with start and end index.
    """
    tstart = None
    tend = None
    for token in doc:
        if token.idx >= start and tstart is None:
            tstart = token.i
        if token.idx >= end and tend is None:
            tend = token.i
        if tstart and tend:
            break
    if tend is None:
        tend = doc[-1].i + 1
    return tstart, tend


class QuantitiesNERComponent:
    """
    Spacy Language component for quantities NER.
    Uses grobid-quantities to extract quantities and  adds them to spacy's Doc.
    """

    def __init__(self, quantities_api_url: str):
        self.client = QuantitiesAPI(quantities_api_url)

    def __call__(self, doc: Doc):
        doc_ents = []
        new_tokens: set[int] = set()

        # send Doc text to grobid-quantities API
        status_code, response = self.client.process_text(doc.text)
        if status_code == 200 and response is not None and "measurements" in response:
            measurements = response["measurements"]

            for measurement in measurements:
                # Check that grobid returned a label we can use
                entity = parse_grobid_measure(measurement, doc.text)
                if entity.label is None:
                    continue

                # Get token start and end index for the label
                start, end = get_token_index_from_label_positions(
                    doc, entity.start, entity.end
                )
                if start is None or end is None:
                    continue

                # Check that the tokens are not already included in an entity.
                # Spacy only allows a token to be in one entity
                # https://github.com/explosion/spaCy/issues/3608
                entity_tokens = set(range(start, end))
                if (
                    any(t.ent_type for t in doc[start:end])
                    or len(new_tokens & entity_tokens) > 0
                ):
                    continue
                new_tokens |= entity_tokens
                new_ent = Span(doc, start, end, label=entity.label)
                doc_ents.append(new_ent)

        doc.ents = list(doc.ents) + doc_ents  # type: ignore
        return doc


@Language.factory(
    "add_quantities", default_config={"quantities_api_url": "http://localhost:8060"}
)
def create_quantities_ner_component(
    nlp, name: str, quantities_api_url: str
) -> QuantitiesNERComponent:
    return QuantitiesNERComponent(quantities_api_url)
