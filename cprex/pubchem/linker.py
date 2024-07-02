import logging
from collections import Counter
from collections.abc import Iterable
from typing import Any

import requests
from requests import HTTPError
from spacy.tokens import Doc

LOGGER = logging.getLogger(__name__)

PUBCHEM_SEARCH_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.84 Safari/537.36",  # noqa: E501
    "Accept": "application/json",
    "Accept-Charset": "ISO-8859-1,utf-8;q=0.7,*;q=0.3",
    "Accept-Encoding": "none",
    "Accept-Language": "en-US,en;q=0.8",
    "Connection": "keep-alive",
}


class PubChemEntityLinker:

    def __init__(self) -> None:
        self._synonyms: dict[str, str] = dict()
        self._properties: dict[str, dict[str, str]] = dict()

    def link(
        self,
        compound: str,
        properties: Iterable[str] = (
            "MolecularFormula",
            "MolecularWeight",
            "CanonicalSMILES",
            "IUPACName",
        ),
    ) -> dict[str, Any] | None:
        if compound.lower() in self._synonyms:
            return self._properties[self._synonyms[compound.lower()]]

        try:
            props = self._rest_api_search(compound, properties)
            if props is None:
                LOGGER.warning(f"Query for '{compound}' returned no properties.")
                return None
            cid = props["CID"]
            self._properties[cid] = props
            synonyms = self._rest_api_search(compound, None)
            if synonyms is not None and "Synonym" in synonyms:
                for synonym in synonyms["Synonym"]:
                    self._synonyms[synonym.lower()] = cid
            return props
        except HTTPError as exc:
            if "PUGREST.NotFound" in exc.response.text:
                LOGGER.warning(f"Compound '{compound}' not found on PubChem.")
            if "PUGREST.Timeout" in exc.response.text:
                LOGGER.error("Timeout error for REST API search query.")
        return None

    def _rest_api_search(
        self,
        compound: str,
        properties: Iterable[str] | None,
    ) -> dict[str, Any] | None:
        """
        Perform a search on PubChem for given compound. Retrieve either a list of
        compound properties, of synonyms if no properties are given.

        Args:
            compound (str): the compound
            properties (Iterable[str] | None): list of properties to search

        Returns:
            dict[str, Any]: dict of properties or synonyms
        """
        url = _get_rest_query_url(properties)
        results = _send_rest_query(url, compound)

        if "InformationList" in results and "Information" in results["InformationList"]:
            synonyms = results["InformationList"]["Information"]
            if len(synonyms) > 1:
                LOGGER.warning(
                    f"Search for compound '{compound}' on PubChem returned more than "
                    "one result."
                )
            return synonyms[0]

        if "PropertyTable" in results and "Properties" in results["PropertyTable"]:
            props = results["PropertyTable"]["Properties"]
            if len(props) > 1:
                LOGGER.warning(
                    f"Search for compound '{compound}' on PubChem returned more than "
                    "one result."
                )
            return props[0]

        return None


def _get_rest_query_url(
    properties: Iterable[str] | None = None,
) -> str:
    """
    Get search query url

    Args:
        properties (Iterable[str] | None, optional): list of properties.
            Defaults to None.

    Returns:
        str: the query url
    """
    url = PUBCHEM_SEARCH_URL + "name"

    if properties:
        url += "/property/" + ",".join(properties)
    else:
        url += "/synonyms"

    url += "/JSON"
    return url


def _send_rest_query(url: str, compound: str) -> Any:
    r = requests.post(url, headers=HEADERS, data={"name": compound})
    r.raise_for_status()
    try:
        LOGGER.debug(r.headers["X-Throttling-Control"])
    except KeyError:
        pass
    return r.json()


LINKER = PubChemEntityLinker()


def link_compounds(docs: Iterable[Doc], min_occurences: int = 3):
    LOGGER.info("Performing Entity Linking.")
    # Count chemical compound occurences
    chems = []
    for doc in docs:
        for ent in doc.ents:
            if ent.label_ == "CHEM":
                chems.append(ent.text)

    # Fetch properties for each compound occurence
    properties: dict[str, dict[str, Any]] = dict()
    occurences = Counter(chems)
    for compound, occurence in occurences.items():
        if (
            occurence >= min_occurences
            and (property := LINKER.link(compound)) is not None
        ):
            properties[compound] = property

    # Set properties for chemical compound spans
    for doc in docs:
        for ent in doc.ents:
            if ent.label_ == "CHEM" and ent.text in properties:
                ent._.props = properties[ent.text]

    return properties


if __name__ == "__main__":
    linker = PubChemEntityLinker()
    print(
        linker.link(
            "2,5-bis(4-hydroxy-3-methoxybenzylidene)cyclopentanone",
        )
    )
