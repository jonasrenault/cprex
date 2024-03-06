from collections.abc import Callable, Iterable
from functools import partial
from pathlib import Path

import spacy
from spacy.language import Language
from spacy.tokens import Doc, DocBin
from spacy.training import Example

# make the config work
from cprex.rel.rel_model import (
    create_classification_layer,  # noqa: F401
    create_instances,  # noqa: F401
    create_relation_model,  # noqa: F401
    create_tensors,  # noqa: F401
)

# make the factory work
from cprex.rel.rel_pipe import make_relation_extractor  # noqa: F401


@spacy.registry.readers("Gold_ents_Corpus.v1")
def create_docbin_reader(file: Path) -> Callable[[Language], Iterable[Example]]:
    return partial(read_files, file)


def read_files(file: Path, nlp: Language) -> Iterable[Example]:
    """Custom reader that keeps the tokenization of the gold data,
    and also adds the gold GGP annotations as we do not attempt to predict these."""
    doc_bin = DocBin().from_disk(file)
    docs = doc_bin.get_docs(nlp.vocab)
    for gold in docs:
        pred = Doc(
            nlp.vocab,
            words=[t.text for t in gold],
            spaces=[t.whitespace_ for t in gold],
        )
        pred.ents = gold.ents
        yield Example(pred, gold)
