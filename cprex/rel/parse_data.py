import json
from pathlib import Path
from typing import Any

from sklearn.model_selection import StratifiedKFold, train_test_split
from spacy.language import Language
from spacy.tokens import Doc, DocBin, Span

from cprex.ner.chem_ner import get_token_index_from_label_positions
from cprex.ner.quantities import fix_grobid_qty_offset_for_special_chars

MAP_LABELS = {
    "Has Value": "has_value",
    # "Has Param": "has_param",
}


def parse_text_and_named_entities(
    example: dict[str, Any], nlp: Language, masking: bool = False
) -> Doc:
    """
    Read an example annotated with label-studio with named entities
    and relations, and create a spacy Doc with this text and named
    entities.

    If masking is True, the text for each named entity in the example
    will be replaced by its label. For example, given an exemple with
    text `The network density of the ANA-Zn(EtIm)2 framework (2.57 T/nm 3 )`
    and named entities `[(4, 19, 'network density', 'PROP'),
    (27, 40, 'ANA-Zn(EtIm)2', 'CHEM'), (52, 63, '2.57 T/nm 3', 'VALUE')]`,
    this will return a Doc with text `The PROP of the CHEM framework (VALUE )`
    and named entities `[(4, 8, 'PROP', 'PROP'), (16, 20, 'CHEM', 'CHEM'),
    (32, 37, 'VALUE', 'VALUE')]`

    Args:
        example (Dict): the annotated example
        nlp (Language): the spacy nlp
        masking (bool, optional): whether to mask entities. Defaults to True.

    Returns:
        Doc: a spacy Doc
    """
    # The example text
    text = example["data"]["text"]

    # Get the named entity annotations
    annotations = example["annotations"][0]["result"]
    ents = []
    for entity in annotations:
        if entity["type"] != "labels":
            continue

        # For each named entity, get its start, end, text and label
        entity_text = entity["value"]["text"]
        start, end = entity["value"]["start"], entity["value"]["end"]
        if not entity_text:
            entity_text = text[start:end]
        start, end = fix_grobid_qty_offset_for_special_chars(
            text,
            start,
            end,
            entity_text,
        )
        ents.append(
            (
                start,
                end,
                entity_text,
                entity["value"]["labels"][0],
                entity["id"],
            )
        )

    ents.sort(key=lambda x: x[0])

    if masking:
        # In case of masking, for each named entity, replace
        # its text by its label and update the token indices accordingly
        masked_ents = []
        offset = 0
        for start, end, entity_text, label, id in ents:
            text = text[: start + offset] + label + text[end + offset :]

            diff = len(label) - len(entity_text)
            masked_ents.append((start + offset, end + offset + diff, label, label, id))
            offset += diff
        ents = masked_ents

    # Finally, create a parsed doc and add the named entities,
    # keeping track of each entity's start token index
    doc = nlp(text)
    spacy_ents = []
    ent_id_to_start = {}
    span_starts = set()
    for start, end, entity_text, label, id in ents:
        # For each named entity, get its token start and end pos
        start, end = get_token_index_from_label_positions(doc[0:], start, end)
        if start is not None and end is not None:
            new_ent = Span(doc, start, end, label=label)
            spacy_ents.append(new_ent)
            span_starts.add(start)
            ent_id_to_start[id] = start
    doc.ents = spacy_ents

    return doc, span_starts, ent_id_to_start


def parse_example(example: dict[str, Any], nlp: Language, masking: bool = False) -> Doc:
    annotations = example["annotations"][0]["result"]

    doc, span_starts, ent_id_to_start = parse_text_and_named_entities(
        example, nlp, masking
    )

    # Parse the relations
    pos = 0
    neg = 0
    rels: dict[tuple[int, int], dict[str, float]] = {}
    for x1 in span_starts:
        for x2 in span_starts:
            rels[(x1, x2)] = {}
    for entity in annotations:
        if entity["type"] != "relation":
            continue

        # Skip creating 'has_param' relations
        if entity["labels"][0] == "Has Param":
            continue

        start = ent_id_to_start[entity["from_id"]]
        end = ent_id_to_start[entity["to_id"]]
        label = MAP_LABELS[entity["labels"][0]]
        if label not in rels[(start, end)]:
            rels[(start, end)][label] = 1.0
            pos += 1

    # The annotation is complete, so fill in zeros where the data is missing
    for x1 in span_starts:
        for x2 in span_starts:
            for label in MAP_LABELS.values():
                if label not in rels[(x1, x2)]:
                    neg += 1
                    rels[(x1, x2)][label] = 0.0
    doc._.rel = rels

    return doc


def count_relations(documents: list[Doc]) -> tuple[int, int]:
    num_has_value = 0
    num_has_param = 0
    for doc in documents:
        num_has_value += sum(rel.get("has_value", 0) for rel in doc._.rel.values())
        num_has_param += sum(rel.get("has_param", 0) for rel in doc._.rel.values())
    return (int(num_has_value), int(num_has_param))


def count_relations_for_sets(
    train_docs: list[Doc], val_docs: list[Doc], test_docs: list[Doc], fold: int = 0
):
    # Counting the number of "has_value" relations per set
    num_has_value_train, _ = count_relations(train_docs)
    num_has_value_dev, _ = count_relations(val_docs)
    num_has_value_test, _ = count_relations(test_docs)
    print(
        f"Number of 'has_value' relations in train set for fold {fold}: "
        f"{num_has_value_train}"
    )
    print(
        f"Number of 'has_value' relations in dev set for fold {fold}: "
        f"{num_has_value_dev}"
    )
    print(
        f"Number of 'has_value' relations in test set for fold {fold}: "
        f"{num_has_value_test}"
    )


def parse_label_studio_annotations(
    json_loc: Path,
    data_dir: Path,
    nlp: Language,
    split_test: bool = True,
    cv: bool = False,
    masking: bool = False,
):
    """
    Parse un fichier d'export de label-studio et crée un corpus
    d'entrainement, validation et test pour un modèle d'extraction
    de relation similaire au projet spacy d'exemple
    https://github.com/explosion/projects/tree/v3/tutorials/rel_component

    Args:
        json_loc (Path): le fichier d'annotations
        data_dir (Path): le dossier d'export des documents
        nlp (Language): le pipeline spacy
        split_test (bool, optional): splitter les données en train, val, test.
            Defaults to True.
        cv (bool, optional): utiliser la cross validation. Defaults to False.
        masking (bool, optional): masquer les entités. Defaults to False.
    """
    docs = []

    with open(json_loc, "r") as jsonfile:
        examples = json.load(jsonfile)
        for example in examples:
            # Only keep docs which have been annotated
            if example["total_annotations"] == 0:
                continue

            try:
                doc = parse_example(example, nlp, masking)
                docs.append(doc)
            except ValueError as exc:
                print(f"Unable to parse example {example['data']['text']}", exc)

    print(f"Parsed {len(docs)} docs.")

    if split_test:
        print("Splitting into train, dev and test sets.")

        # Define ratios
        train_ratio = 0.8
        test_ratio = 0.10
        validation_ratio = 0.10

        if cv:
            # Number of splits for cross-validation
            n_splits = 5
            print(f"Splitting into {n_splits} fold cross-validation sets.")

            # StratifiedKFold for maintaining class distribution in each split
            skf = StratifiedKFold(
                n_splits=n_splits,
                shuffle=True,
            )

            for fold, (train_index, test_index) in enumerate(
                skf.split(docs, y=["has_value" in doc._.rel.values() for doc in docs])
            ):
                train_docs, test_docs = [docs[i] for i in train_index], [
                    docs[i] for i in test_index
                ]

                # Further split the test set into validation and test sets
                val_docs, test_docs = train_test_split(
                    test_docs, test_size=test_ratio / (test_ratio + validation_ratio)
                )

                # Save each fold
                docbin = DocBin(docs=train_docs, store_user_data=True)
                docbin.to_disk(data_dir / f"train_fold_{fold}.spacy")
                docbin = DocBin(docs=val_docs, store_user_data=True)
                docbin.to_disk(data_dir / f"dev_fold_{fold}.spacy")
                docbin = DocBin(docs=test_docs, store_user_data=True)
                docbin.to_disk(data_dir / f"test_fold_{fold}.spacy")

                print(
                    f"Saved Fold {fold}: {len(train_docs)} train docs, {len(val_docs)} "
                    f"dev docs, and {len(test_docs)} test docs."
                )
                count_relations_for_sets(train_docs, val_docs, test_docs, fold)
        else:
            train_docs, test_docs = train_test_split(docs, test_size=1 - train_ratio)
            val_docs, test_docs = train_test_split(
                test_docs, test_size=test_ratio / (test_ratio + validation_ratio)
            )
            docbin = DocBin(docs=train_docs, store_user_data=True)
            docbin.to_disk(data_dir / "train.spacy")
            docbin = DocBin(docs=val_docs, store_user_data=True)
            docbin.to_disk(data_dir / "dev.spacy")
            docbin = DocBin(docs=test_docs, store_user_data=True)
            docbin.to_disk(data_dir / "test.spacy")
            print(
                f"Saved {len(train_docs)} train docs, {len(val_docs)} dev docs and "
                f"{len(test_docs)} test docs."
            )
            count_relations_for_sets(train_docs, val_docs, test_docs)

    else:
        print("Splitting into train and dev sets (no tests).")

        # Define ratios
        train_ratio = 0.9
        validation_ratio = 0.10
        train_docs, val_docs = train_test_split(docs, test_size=1 - train_ratio)
        docbin = DocBin(docs=train_docs, store_user_data=True)
        docbin.to_disk(data_dir / "train.spacy")
        docbin = DocBin(docs=val_docs, store_user_data=True)
        docbin.to_disk(data_dir / "dev.spacy")
        print(f"Saved {len(train_docs)} train docs and {len(val_docs)} dev docs.")
