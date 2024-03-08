# CPREx - Chemical Properties Relation Extraction

CPREx is an end to end tool for Named Entity Recognition (NER) and Relation Extraction (RE) specifically designed for chemical compounds and their properties. The goal of the tool is to identify, extract and link chemical compounds and their properties from scientific literature. For ease of use, CPREx provides a custom [spacy](https://spacy.io/) pipeline to perform NER and RE.

The pipeline performs the following steps

```mermaid
flowchart LR
    crawler("`**crawler**
    fetch PDF articles
    from online archives`")
    parser("`**parser**
    Extract text from PDF`")
    crawler --> parser
    parser --> ner
    ner("`**NER**
    extract named entities`")
    ner --> chem[Chem] --> rel
    ner --> prop[Property] --> rel
    ner --> quantity[Value] --> rel
    rel("`**Relation Extraction**
    link entities`")
    rel --> res
    res("`**(Chem, Property, Value)**
    *2,2'-Binaphthalene*, ΔHfus, 38.9 kJ/mol`")

```
