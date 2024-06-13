# CPREx - Chemical Properties Relation Extraction

[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
![python_version](https://img.shields.io/badge/Python-%3E=3.11-blue)

CPREx is an end to end tool for Named Entity Recognition (NER) and Relation Extraction (RE) specifically designed for chemical compounds and their properties. The goal of the tool is to identify, extract and link chemical compounds and their properties from scientific literature. For ease of use, CPREx provides a custom [spaCy](https://spacy.io/) pipeline to perform NER and RE.

The pipeline performs the following steps

```mermaid
flowchart LR
    crawler("`**crawler**
    fetch PDF articles
    from online archives`")
    parser("`**parser**
    Extract text
    from PDF`")
    crawler --> parser
    parser --> ner
    ner("`**NER**
    extract named
    entities`")
    ner --> chem["`**Chem**
    *1,3,5-Triazine*
    *Zinc bromide*
    *C₃H₄N₂*`"] --> rel
    ner --> prop["`**Property**
    *fusion enthalpy*
    *Tc*`"] --> rel
    ner --> quantity["`**Value**
    *169°C*
    *21.49 kJ/mol*`"] --> rel
    rel("`**Relation Extraction**
    link entities`")
    rel --> res
    res("`**(Chem, Property, Value)**
    *2,2'-Binaphthalene, ΔHfus, 38.9 kJ/mol*`")
```

## Installation

CPREx works with a recent version of python (**>=python 3.11**). Make sure to install CPREx in a virtual environment of your choice.

CPREx depends on [GROBID](https://github.com/kermitt2/grobid) and its extension [grobid-quantities](https://github.com/lfoppiano/grobid-quantities) for parsing PDF documents and extracting quantities from their text. In order to install and run GROBID, a JDK must also be installed on your machine. [GROBID currently supports](https://grobid.readthedocs.io/en/latest/Install-Grobid/) JDKs from **1.11 to 1.17**.

### Install via PyPI

You can install CPREx directly with pip:

```console
pip install cprex
```

### Install from github

This installation is recommended for users who want to customize the pipeline or train some models on their own dataset.

Clone the repository and install the project in your python environment.

```console
git clone git@github.com:jonasrenault/cprex.git
cd cprex
pip install --editable .
```

Any modifications you make to the cprex codebase will be immediatly reflected thanks to the `--editable` option.

### Install grobid and models

#### Installing and running grobid

CPREx depends on [GROBID](https://github.com/kermitt2/grobid) and its extension [grobid-quantities](https://github.com/lfoppiano/grobid-quantities) for parsing PDF documents and extracting quantities from their text. For convenience, CPREx provides a command line interface (CLI) to install grobid and start a grobid server.

Run

```console
cprex install-grobid
```

to install a grobid server and the grobid-quantities extension (by default, grobid and models required by CPREx are installed in a `.cprex` directory in your home directory).

Run

```console
cprex start-grobid
```

to start a grobid server and enable parsing of PDF documents from CPREx.

#### Installing NER et REL models

To perform Named Entity Recognition (NER) of chemical compounds and Relation Extraction (RE), CPREx requires some pretrained models. These models can be installed by running

```console
cprex install-models
```

This will install a [PubmedBert model](https://ftp.ncbi.nlm.nih.gov/pub/lu/BC7-NLM-Chem-track/) finetuned on the NLM-CHEM corpus for extraction of chemical named entities. This model was finetuned by the [BioCreative VII track](https://biocreative.bioinformatics.udel.edu/tasks/biocreative-vii/track-2/).

It will also install a [RE model](https://github.com/jonasrenault/cprex/releases/tag/v0.3.0) pre-trained on our own annotated dataset.

#### Installing a base spacy model

A base [spaCy model](https://github.com/explosion/spacy-models/releases), such as `en_core_web_sm`, is required for tokenization, lemmatization, and all other features offered by spaCy. To install a spaCy model, you can run

```console
python -m spacy download en_core_web_sm
```

or directly install it with pip by specifying the model's url

```console
pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1.tar.gz
```
