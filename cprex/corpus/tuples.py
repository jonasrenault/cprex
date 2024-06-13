from collections.abc import Iterable
from dataclasses import dataclass

from spacy.tokens import Doc, Span


@dataclass
class ChemPropValueRelation:
    doc: Doc
    value: Span
    properties: list[Span] | None = None
    chemicals: list[Span] | None = None

    def add_head(self, head: Span):
        if head.label_ == "CHEM":
            self.add_chemicals(head)
        else:
            self.add_property(head)

    def add_property(self, property: Span):
        if self.properties is None:
            self.properties = [property]
        else:
            self.properties.append(property)

    def add_chemicals(self, chemical: Span):
        if self.chemicals is None:
            self.chemicals = [chemical]
        else:
            self.chemicals.append(chemical)

    def to_dict(self):
        res = {
            "title": self.doc._.title,
            "doi": self.doc._.doi,
            "section": self.doc._.section,
            "text": self.doc.text,
            "value": entity_to_dict(self.value),
        }
        if self.properties is not None:
            res["properties"] = [entity_to_dict(prop) for prop in self.properties]
        if self.chemicals is not None:
            res["chemicals"] = [entity_to_dict(chem) for chem in self.chemicals]
        return res


def entity_to_dict(entity: Span):
    res = {
        "text": entity.text,
        "label": entity.label_,
        "start": entity.start_char,
        "end": entity.end_char,
    }
    if entity.label_ in ["FORMULA", "PROP"]:
        res["type"] = entity.ent_id_
    return res


def extract_tuple_relations(
    doc: Doc, threshold: float = 0.45
) -> Iterable[ChemPropValueRelation]:
    """
    Extract ChemPropValueRelation tuples from a spacy Doc.

    Args:
        doc (Doc): the doc
        threshold (float, optional): threshold for relations. Defaults to 0.45.

    Returns:
        Iterable[ChemPropValueRelation]: a list of ChemPropValueRelations
    """
    ent_start_to_ent = {}
    for ent in doc.ents:
        ent_start_to_ent[ent.start] = ent

    tuples: dict[int, ChemPropValueRelation] = {}
    for pair, rel_dict in doc._.rel.items():
        for rel_label, prob in rel_dict.items():
            if prob >= threshold:
                value = ent_start_to_ent[pair[1]]
                head = ent_start_to_ent[pair[0]]
                if pair[1] not in tuples:
                    tuples[pair[1]] = ChemPropValueRelation(doc, value)
                tuple_ = tuples[pair[1]]
                tuple_.add_head(head)

    return tuples.values()
