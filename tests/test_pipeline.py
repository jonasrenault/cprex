from cprex.pipeline import get_pipeline


def test_get_pipeline_returns_pipelin():
    nlp = get_pipeline(enable_ner_pipelines=False, enable_rel_pipeline=False)

    assert tuple(name for name, _ in nlp.pipeline) == (
        "tok2vec",
        "tagger",
        "parser",
        "attribute_ruler",
        "lemmatizer",
    )
