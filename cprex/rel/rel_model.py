from collections.abc import Callable

import spacy
from spacy.tokens import Doc, Span
from thinc.api import Linear, Logistic, Model, chain
from thinc.types import Floats2d, Ints1d, Ragged, cast

from cprex.ner.quantities import PROPERTY_TO_UNITS


@spacy.registry.architectures("rel_model.v1")
def create_relation_model(
    create_instance_tensor: Model[list[Doc], Floats2d],
    classification_layer: Model[Floats2d, Floats2d],
) -> Model[list[Doc], Floats2d]:
    with Model.define_operators({">>": chain}):
        model = create_instance_tensor >> classification_layer
        model.attrs["get_instances"] = create_instance_tensor.attrs["get_instances"]
    return model


@spacy.registry.architectures("rel_classification_layer.v1")
def create_classification_layer(
    nO: int | None = None, nI: int | None = None
) -> Model[Floats2d, Floats2d]:
    with Model.define_operators({">>": chain}):
        return Linear(nO=nO, nI=nI) >> Logistic()


@spacy.registry.misc("rel_instance_generator.v1")
def create_instances(max_length: int) -> Callable[[Doc], list[tuple[Span, Span]]]:
    def get_instances(doc: Doc) -> list[tuple[Span, Span]]:
        instances = []
        for ent1 in doc.ents:
            for ent2 in doc.ents:
                if can_link_instances(ent1, ent2, max_length):
                    instances.append((ent1, ent2))
        return instances

    return get_instances


@spacy.registry.architectures("rel_instance_tensor.v1")
def create_tensors(
    tok2vec: Model[list[Doc], list[Floats2d]],
    pooling: Model[Ragged, Floats2d],
    get_instances: Callable[[Doc], list[tuple[Span, Span]]],
) -> Model[list[Doc], Floats2d]:
    return Model(
        "instance_tensors",
        instance_forward,
        layers=[tok2vec, pooling],
        refs={"tok2vec": tok2vec, "pooling": pooling},
        attrs={"get_instances": get_instances},
        init=instance_init,
    )


def instance_forward(
    model: Model[list[Doc], Floats2d], docs: list[Doc], is_train: bool
) -> tuple[Floats2d, Callable]:
    pooling = model.get_ref("pooling")
    tok2vec = model.get_ref("tok2vec")
    get_instances = model.attrs["get_instances"]
    all_instances = [get_instances(doc) for doc in docs]
    tokvecs, bp_tokvecs = tok2vec(docs, is_train)

    ents = []
    lengths = []

    for doc_nr, (instances, tokvec) in enumerate(zip(all_instances, tokvecs)):
        token_indices = []
        for instance in instances:
            for ent in instance:
                token_indices.extend([i for i in range(ent.start, ent.end)])
                lengths.append(ent.end - ent.start)
        ents.append(tokvec[token_indices])
    lengths_arr = cast(Ints1d, model.ops.asarray(lengths, dtype="int32"))
    entities = Ragged(model.ops.flatten(ents), lengths_arr)
    pooled, bp_pooled = pooling(entities, is_train)

    # Reshape so that pairs of rows are concatenated
    relations = model.ops.reshape2f(pooled, -1, pooled.shape[1] * 2)

    def backprop(d_relations: Floats2d) -> list[Doc]:
        d_pooled = model.ops.reshape2f(d_relations, d_relations.shape[0] * 2, -1)
        d_ents = bp_pooled(d_pooled).data
        d_tokvecs = []
        ent_index = 0
        for doc_nr, instances in enumerate(all_instances):
            shape = tokvecs[doc_nr].shape
            d_tokvec = model.ops.alloc2f(*shape)
            count_occ = model.ops.alloc2f(*shape)
            for instance in instances:
                for ent in instance:
                    d_tokvec[ent.start : ent.end] += d_ents[ent_index]
                    count_occ[ent.start : ent.end] += 1
                    ent_index += ent.end - ent.start
            d_tokvec /= count_occ + 0.00000000001
            d_tokvecs.append(d_tokvec)

        d_docs = bp_tokvecs(d_tokvecs)
        return d_docs

    return relations, backprop


def instance_init(
    model: Model, X: list[Doc] | None = None, Y: Floats2d | None = None
) -> Model:
    tok2vec = model.get_ref("tok2vec")
    if X is not None:
        tok2vec.initialize(X)
    return model


def can_link_instances(ent1: Span, ent2: Span, max_length: int):
    if ent1 == ent2:
        return False

    if max_length and abs(ent2.start - ent1.start) > max_length:
        return False

    # Only link CHEM, PROP or FORMULA entities to VALUES entities
    valid_types = ent1.label_ in ("CHEM", "PROP", "FORMULA") and ent2.label_ not in (
        "CHEM",
        "PROP",
        "FORMULA",
    )
    if not valid_types:
        return False

    # Safety check: if we're linking a Property to a quantity, and we know the
    # quantity's unit, check that the unit corresponds to the property,
    # i.e. we're not linking a density to a length
    if ent1.label_ in ("PROP", "FORMULA") and ent2.label_ != "VALUE":
        property_type = ent1.ent_id_
        quantity_unit = ent2.label_
        if (
            property_type
            and property_type in PROPERTY_TO_UNITS
            and PROPERTY_TO_UNITS[property_type]
            and quantity_unit not in PROPERTY_TO_UNITS[property_type]
        ):
            return False

    return True
