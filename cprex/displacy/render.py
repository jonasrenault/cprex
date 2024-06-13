from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from spacy.displacy import get_doc_settings, parse_deps, parse_ents, parse_spans
from spacy.displacy.render import DependencyRenderer, EntityRenderer, SpanRenderer
from spacy.displacy.templates import (
    TPL_ENTS,
    TPL_FIGURE,
    TPL_KB_LINK,
    TPL_PAGE,
    TPL_SPAN_RTL,
    TPL_SPAN_SLICE_RTL,
    TPL_SPAN_START_RTL,
    TPL_TITLE,
)
from spacy.errors import Errors
from spacy.tokens import Doc, Span
from spacy.util import escape_html, is_in_jupyter, minify_html

from cprex.displacy.templates import (
    TPL_ENT,
    TPL_ENT_RTL,
    TPL_SPAN,
    TPL_SPAN_END,
    TPL_SPAN_END_INV,
    TPL_SPAN_SLICE,
    TPL_SPAN_START,
    TPL_SPAN_START_INV,
)

DEFAULT_LANG = "en"
DEFAULT_DIR = "ltr"
DEFAULT_ENTITY_COLOR = "#ddd"
DEFAULT_LABEL_COLORS = {
    "CHEM": "pink",
    "PROP": "#feca74",
    "FORMULA": "#c887fb",
    "TEMPERATURE": "#7aecec",
    "DENSITY": "#7aecec",
    "TIME": "#ddd",
    "PERCENT": "#ddd",
    "ENTHALPY": "#7aecec",
    "MOLAR VOLUME": "#7aecec",
    "ABSORPTIVITY": "#7aecec",
    "SOLUBILITY": "#7aecec",
    "ENERGY": "#7aecec",
    "MAXIMUM ENERGY PRODUCT": "#7aecec",
    "VELOCITY": "#7aecec",
    "HEAT CAPACITY": "#7aecec",
    "THERMAL CONDUCTIVITY": "#7aecec",
    "DYNAMIC VISCOSITY": "#7aecec",
}
COLOR_SCALE = [
    "#7fc97f",
    "#beaed4",
    "#fdc086",
    "#ffff99",
    "#386cb0",
    "#f0027f",
    "#bf5b17",
    "#666666",
]


@dataclass
class NamedEntity:
    start: int
    end: int
    label: str
    id: str
    kb_id: str = ""
    kb_url: str = "#"


@dataclass
class Relation:
    head: str
    tail: str
    label: str
    id: str


@dataclass
class RelRendererInput:
    text: str
    ents: list[NamedEntity]
    rels: list[Relation]
    settings: dict[str, Any] | None
    title: str | None = None


def render_docs(
    docs: list[Doc],
    jupyter: bool = True,
    colors: dict[str, str] = DEFAULT_LABEL_COLORS,
) -> str:
    """
    Render a list of docs. Convenience method to display section titles
    for each doc.

    Args:
        docs (list[Doc]): list of docs to render
        jupyter (bool, optional): in Jupyter Notebook. Defaults to True.
        colors (dict[str, str], optional): colors for Named Entity labels.
            Defaults to DEFAULT_LABEL_COLORS.
    """
    display_docs = []
    previous_title = None
    for doc in docs:
        doc.user_data["title"] = (
            doc._.section
            if previous_title != doc._.section and doc._.section != ""
            else None
        )
        previous_title = doc._.section
        display_docs.append(doc)

    return render(display_docs, style="rel", jupyter=jupyter, options={"colors": colors})


def render(
    docs: Iterable[Doc | Span | dict] | Doc | Span | dict,
    style: str = "rel",
    page: bool = False,
    minify: bool = False,
    jupyter: bool | None = None,
    options: dict[str, Any] = {},
    manual: bool = False,
) -> str:
    """
    Render displaCy visualisation.
    DOCS: https://spacy.io/api/top-level#displacy.render
    USAGE: https://spacy.io/usage/visualizers

    Args:
        docs (Iterable[Doc  |  Span  |  dict] | Doc | Span | dict): Document(s) to
            visualize. A dict is only allowed when `manual` is set to True.
        style (str, optional): Visualisation style. Defaults to "rel".
        page (bool, optional): Render markup as full HTML page. Defaults to False.
        minify (bool, optional): Minify HTML markup. Defaults to False.
        jupyter (bool | None, optional): Override Jupyter auto-detection.
            Defaults to None.
        options (dict[str, Any], optional): Visualiser-specific options, eg. colors.
            Defaults to {}.
        manual (bool, optional): Don't parse `Doc`and instead expect a dict/list
            of dicts. Defaults to False.

    Raises:
        ValueError: if invalid input
        ValueError: if style is not one of ('dep', 'ent', 'span', 'rel').

    Returns:
        str: Rendered HTML markup.
    """
    factories = {
        "dep": (DependencyRenderer, parse_deps),
        "ent": (EntityRenderer, parse_ents),
        "span": (SpanRenderer, parse_spans),
        "rel": (RelRenderer, parse_rels),
    }
    if style not in factories:
        raise ValueError(Errors.E087.format(style=style))
    if isinstance(docs, (Doc, Span, dict)):
        docs = [docs]
    docs = [obj if not isinstance(obj, Span) else obj.as_doc() for obj in docs]
    if not all(isinstance(obj, (Doc, Span, dict)) for obj in docs):
        raise ValueError(Errors.E096)
    renderer_func, converter = factories[style]
    renderer = renderer_func(options=options)
    parsed = (
        [converter(doc, options) for doc in docs] if not manual else docs  # type: ignore
    )
    if manual:
        for doc in docs:
            if isinstance(doc, dict) and "ents" in doc:
                doc["ents"] = sorted(doc["ents"], key=lambda x: (x["start"], x["end"]))
    html = renderer.render(parsed, page=page, minify=minify).strip()  # type: ignore
    if jupyter or (jupyter is None and is_in_jupyter()):
        # return HTML rendered by IPython display()
        # See #4840 for details on span wrapper to disable mathjax
        from IPython.core.display import HTML, display

        return display(HTML('<span class="tex2jax_ignore">{}</span>'.format(html)))
    return html


def parse_rels(doc: Doc, options: dict[str, Any] = {}) -> RelRendererInput:
    kb_url_template = options.get("kb_url_template", None)
    ents = []
    ent_start_to_id = {}
    for ent in doc.ents:
        named_entity = NamedEntity(
            start=ent.start_char,
            end=ent.end_char,
            label=ent.label_,
            id=str(uuid4()),
            kb_id=ent.kb_id_ if ent.kb_id_ else "",
            kb_url=kb_url_template.format(ent.kb_id_) if kb_url_template else "#",
        )
        ents.append(named_entity)
        ent_start_to_id[ent.start] = named_entity.id
    title = doc.user_data.get("title", None) if hasattr(doc, "user_data") else None
    settings = get_doc_settings(doc)

    threshold: float = options.get("threshold", 0.45)
    rels = []
    for pair, rel_dict in doc._.rel.items():
        for rel_label, prob in rel_dict.items():
            if prob >= threshold:
                rels.append(
                    Relation(
                        head=ent_start_to_id[pair[0]],
                        tail=ent_start_to_id[pair[1]],
                        label=f"{rel_label} ({prob:.02f})",
                        id=str(uuid4()),
                    )
                )

    return RelRendererInput(
        text=doc.text, ents=ents, rels=rels, settings=settings, title=title
    )


class RelRenderer:
    """
    Render named entities and relations as HTML.
    """

    style = "rel"

    def __init__(self, options: dict[str, Any] = {}) -> None:
        """
        Initialize renderer.

        Args:
            options (dict[str, Any], optional): Visualiser-specific options
                (colors, ents). Defaults to {}.
        """
        colors = dict(DEFAULT_LABEL_COLORS)
        colors.update(options.get("colors", {}))
        self.default_color = DEFAULT_ENTITY_COLOR
        self.colors = {label.upper(): color for label, color in colors.items()}
        self.ents = options.get("ents", None)
        if self.ents is not None:
            self.ents = [ent.upper() for ent in self.ents]
        self.direction = DEFAULT_DIR
        self.lang = DEFAULT_LANG
        # These values are in px
        self.top_offset = options.get("top_offset", 40)
        # This is how far under the top offset the span labels appear
        self.span_label_offset = options.get("span_label_offset", 20)
        self.offset_step = options.get("top_offset_step", 17)

        template = options.get("template")
        if template:
            self.ent_template = template
        else:
            if self.direction == "rtl":
                self.ent_template = TPL_ENT_RTL
                self.span_template = TPL_SPAN_RTL
                self.span_slice_template = TPL_SPAN_SLICE_RTL
                self.span_start_template = TPL_SPAN_START_RTL
                self.span_start_inv_template = TPL_SPAN_START_INV
                self.span_end_template = TPL_SPAN_END
                self.span_end_inv_template = TPL_SPAN_END_INV
            else:
                self.ent_template = TPL_ENT
                self.span_template = TPL_SPAN
                self.span_slice_template = TPL_SPAN_SLICE
                self.span_start_template = TPL_SPAN_START
                self.span_start_inv_template = TPL_SPAN_START_INV
                self.span_end_template = TPL_SPAN_END
                self.span_end_inv_template = TPL_SPAN_END_INV

    def render(
        self, parsed: list[RelRendererInput], page: bool = False, minify: bool = False
    ) -> str:
        """
        Render complete markup.

        Args:
            parsed (list[RelRendererInput]): Entities and relations to render.
            page (bool, optional): render as full HTML page. Defaults to False.
            minify (bool, optional): minify HTML markup. Defaults to False.

        Returns:
            str: Rendered HTML markup.
        """
        rendered = []
        for i, p in enumerate(parsed):
            if i == 0:
                settings = p.settings if p.settings else {}
                self.direction = settings.get("direction", DEFAULT_DIR)
                self.lang = settings.get("lang", DEFAULT_LANG)
            rendered.append(self.render_spans(p.text, p.ents, p.rels, p.title))

        if page:
            docs = "".join([TPL_FIGURE.format(content=doc) for doc in rendered])
            markup = TPL_PAGE.format(content=docs, lang=self.lang, dir=self.direction)
        else:
            markup = "".join(rendered)
        if minify:
            return minify_html(markup)
        return markup

    def render_spans(
        self,
        text: str,
        ents: list[NamedEntity],
        rels: list[Relation],
        title: str | None,
    ) -> str:
        """
        Render spans of text with Named Entities highlighted and relations as lines
        underneath. Spans as rendered as either Named Entities or text in between Named
        Entities.

        Args:
            text (str): the document's text to render
            ents (list[NamedEntity]): list of named entities with their labels
            rels (list[Relation]): list of relations between named entities
            title (str | None): Document title set in Doc.user_data["title"]

        Returns:
            str: The rendered HTML of the text with Named Entities and relations.
        """
        per_token_info = self._assemble_per_fragment_info(text, ents, rels)
        markup = self._render_markup(per_token_info)
        markup = TPL_ENTS.format(content=markup, dir=self.direction)
        if title:
            markup = TPL_TITLE.format(title=title) + markup
        return markup

    def _assemble_per_fragment_info(
        self,
        text: str,
        ents: list[NamedEntity],
        rels: list[Relation],
    ):
        per_fragment_info = []
        offset = 0
        open_relations: dict[str, dict[str, Any]] = {}

        for ent in ents:
            offset_text = text[offset : ent.start]
            if offset_text.strip():
                per_fragment_info.append(
                    {
                        "text": escape_html(offset_text),
                        "rels": list(open_relations.values()),
                    }
                )

            fragment_info: dict[str, Any] = {
                "text": escape_html(text[ent.start : ent.end])
            }

            if self.ents is None or ent.label.upper() in self.ents:
                fragment_info["label"] = ent.label
                fragment_info["bg"] = self.colors.get(
                    ent.label.upper(), self.default_color
                )
                fragment_info["kb_link"] = (
                    TPL_KB_LINK.format(kb_id=ent.kb_id, kb_url=ent.kb_url)
                    if ent.kb_id
                    else ""
                )

            render_slots_taken = set(r["render_slot"] for r in open_relations.values())
            fragment_relations = []
            for rel in rels:
                if rel.head == ent.id or rel.tail == ent.id:
                    if rel.id in open_relations:
                        render_slot = open_relations[rel.id]["render_slot"]
                        color = open_relations[rel.id]["color"]
                        rtl = rel.head == ent.id
                        del open_relations[rel.id]
                    else:
                        render_slot, color = get_render_slot_and_color(render_slots_taken)
                        render_slots_taken.add(render_slot)
                        open_relations[rel.id] = {
                            "render_slot": render_slot,
                            "label": rel.label,
                            "color": color,
                            "id": rel.id,
                        }
                        rtl = rel.tail == ent.id

                    fragment_relations.append(
                        {
                            "render_slot": render_slot,
                            "label": rel.label,
                            "color": color,
                            "is_head": rel.head == ent.id,
                            "is_tail": rel.tail == ent.id,
                            "rtl": rtl,
                            "id": rel.id,
                        }
                    )

                elif rel.id in open_relations:
                    fragment_relations.append(open_relations[rel.id])
            fragment_info["rels"] = fragment_relations

            per_fragment_info.append(fragment_info)
            offset = ent.end

        per_fragment_info.append({"text": escape_html(text[offset:])})
        return per_fragment_info

    def _render_markup(self, per_fragment_info: list[dict[str, Any]]) -> str:
        """
        Render the markup from per-fragment information

        Args:
            per_fragment_info (list[dict[str, Any]]): fragment metadata for rendering.

        Returns:
            str: the rendered HTML markup.
        """
        markup = ""
        for fragment in per_fragment_info:
            text_content = (
                self.ent_template.format(**fragment)
                if "label" in fragment
                else fragment["text"]
            )
            relations = fragment.get("rels", [])
            if relations:
                slices, starts = self._get_spans(relations)
                max_render_slot = max(rel["render_slot"] for rel in relations)
                total_height = (
                    self.top_offset
                    + self.span_label_offset
                    + (self.offset_step * (max_render_slot - 1))
                )
                markup += self.span_template.format(
                    text=text_content,
                    span_slices=slices,
                    span_starts=starts,
                    total_height=total_height,
                )
            else:
                markup += text_content

        return markup

    def _get_spans(self, relations: list[dict[str, Any]]) -> tuple[str, str]:
        """
        Get the rendered markup of all Span slices (relations).

        Args:
            relations (list[dict[str, Any]]): relations metadata for each fragment.

        Returns:
            tuple[str, str]: the rendered relation spans.
        """
        span_slices = []
        span_starts = []
        for relation in relations:
            span_slices.append(self._get_span_slice(relation))
            span_starts.append(self._get_span_start(relation))
        return "".join(span_slices), "".join(span_starts)

    def _get_span_slice(self, relation: dict[str, Any]) -> str:
        color = relation["color"]
        top_offset = self.top_offset + (self.offset_step * (relation["render_slot"] - 1))
        is_tail = "is_tail" in relation and relation["is_tail"]
        is_rtl = "rtl" in relation and relation["rtl"]
        if is_tail and is_rtl:
            return self.span_end_inv_template.format(bg=color, top_offset=top_offset)
        if is_tail:
            return self.span_end_template.format(
                bg=color,
                top_offset=top_offset,
            )
        return self.span_slice_template.format(
            bg=color,
            top_offset=top_offset,
        )

    def _get_span_start(self, relation: dict[str, Any]) -> str:
        color = relation["color"]
        top_offset = self.top_offset + (self.offset_step * (relation["render_slot"] - 1))
        is_head = "is_head" in relation and relation["is_head"]
        is_rtl = "rtl" in relation and relation["rtl"]
        if is_head and is_rtl:
            return self.span_start_inv_template.format(
                bg=color, top_offset=top_offset, label=relation["label"], kb_link=""
            )

        if is_head:
            return self.span_start_template.format(
                bg=color, top_offset=top_offset, label=relation["label"], kb_link=""
            )

        return ""


def get_render_slot_and_color(render_slots_taken: set[int]) -> tuple[int, str]:
    free_slots = set(range(1, len(render_slots_taken) + 1)) - render_slots_taken
    render_slot = min(free_slots) if free_slots else len(render_slots_taken) + 1
    color = COLOR_SCALE[(render_slot - 1) % len(COLOR_SCALE)]
    return render_slot, color
