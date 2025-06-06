"""Utility functions specific to Salex."""

import karp.foundation.json as json
from copy import deepcopy
from enum import Enum, global_enum
from dataclasses import dataclass
import re
from karp.lex.domain.dtos import EntryDto
import utils.markup_parser as markup_parser
import lark
from typing import Union
from utils.testing import add_write_via_handler, TestWarning, highlight, link_cell
from urllib.parse import quote


def entry_is_visible(entry):
    return entry.get("visas", True)


def entry_is_visible_in_printed_book(entry):
    return entry_is_visible(entry) and not entry.get("endastDigitalt", False)


def is_visible(path, entry, test=entry_is_visible):
    path = json.make_path(path)
    for i in range(len(path) + 1):
        subpath = json.get_path(path[:i], entry)
        if isinstance(subpath, dict) and not test(subpath):
            return False

    return True


def trim_invisible(data, test=entry_is_visible):
    paths = list(json.all_paths(data))  # compute up front since we will be modifying data
    for path in paths:
        if not json.has_path(path, data):
            continue  # already deleted

        value = json.get_path(path, data)
        if isinstance(value, dict) and not test(value):
            json.del_path(path, data)


def visible_part(data, test=entry_is_visible):
    data = deepcopy(data)
    trim_invisible(data, test)
    return data


@global_enum
class Namespace(Enum):
    SO = 0
    SAOL = 1

    @property
    def path(self):
        match self:
            case Namespace.SO:
                return "so"
            case Namespace.SAOL:
                return "saol"


@global_enum
class IdType(Enum):
    LNR = 0
    XNR = 1
    KCNR = 2
    INR = 3
    TEXT = 4
    UNKNOWN = 5


@dataclass(frozen=True)
class Id:
    namespace: Namespace
    type: IdType
    id: Union[str, "TextId"]

    def format(self):
        match self.type:
            case IdType.LNR:
                return f"lnr{self.id}"
            case IdType.XNR:
                return f"xnr{self.id}"
            case IdType.KCNR:
                return f"inr{self.id}"
            case IdType.INR:
                return f"(idiom) {self.id}"
            case IdType.TEXT:
                return self.id.format()
            case IdType.UNKNOWN:
                return f"(okänt format) {self.id}"


@dataclass(frozen=True)
class TextId:
    ortografi: str
    homografNr: int | None
    # TODO also add lemmaNr: int | None for e.g. [i katt 1]
    # Not included now because not sure how it works if some huvudbetydelser have visas=False

    def format(self):
        return " ".join(str(x) for x in [self.homografNr, self.ortografi] if x is not None)


@dataclass
class IdLocation:
    entry: EntryDto
    namespace: Namespace
    path: list[str]
    text: str

    @property
    def visible(self):
        return is_visible(self.path, self.entry.entry.get(self.namespace.path, {}))

    @property
    def field(self):
        return json.path_str(self.path, strip_positions=True)


id_fields = {
    SO: {
        "l_nr": LNR,
        "huvudbetydelser.x_nr": XNR,
        "huvudbetydelser.underbetydelser.kc_nr": KCNR,
        "huvudbetydelser.idiom.i_nr": INR,
        "variantformer.l_nr": LNR,
        "vnomen.l_nr": LNR,
        "förkortningar.l_nr": LNR,
    },
    SAOL: {
        "id": LNR,
        "huvudbetydelser.id": XNR,
        "variantformer.id": LNR,
    },
}

non_variant_id_fields = {SO: {"l_nr"}, SAOL: {"id"}}


ref_fields = {
    SO: {
        "huvudbetydelser.hänvisningar.hänvisning": None,
        "huvudbetydelser.morfex.hänvisning": None,
        "huvudbetydelser.underbetydelser.hänvisningar.hänvisning": None,
        "huvudbetydelser.underbetydelser.morfex.hänvisning": None,
        "huvudbetydelser.idiom.hänvisning": INR,
        "vnomen.hänvisning": None,
        "relaterade_verb.refid": LNR,
    },
    SAOL: {
        "moderverb": LNR,
        # "variantformer.id": LNR,
    },
}

refid_ref_fields = {
    SO: {},
    SAOL: {
        "huvudlemma",
        "enbartDigitalaHänvisningar.hänvisning",
        "huvudbetydelser.hänvisningar.hänvisning",
    },
}

no_refid_fields = {
    SO: {
        "uttal.fonetikparentes",
    },
    SAOL: {},
}

freetext_fields = {
    SO: {
        "huvudbetydelser.definition",
        "huvudbetydelser.definitionstillägg",
    },
    SAOL: {"huvudbetydelser.definition", "sammansättningskommentar"},
}


def find_ids(entry):
    for namespace in id_fields:
        if namespace.path not in entry.entry:
            continue
        sub_entry = entry.entry[namespace.path]

        for field, kind in id_fields[namespace].items():
            for path in json.expand_path(field, sub_entry):
                value = json.get_path(path, sub_entry)
                yield Id(namespace, kind, value), IdLocation(entry, namespace, path, value)

        yield from text_ids(entry, namespace, include_linked=False)


def text_ids(entry, namespace, include_linked=True):
    sub_entry = entry.entry.get(namespace.path, {})
    for field, kind in id_fields[namespace].items():
        if kind == LNR:
            for path in json.expand_path(field, sub_entry):
                parent = path[:-1]
                if not include_linked and json.has_path(parent + ["moderverb"], sub_entry):
                    continue

                if not parent:  # top-level entry
                    ortografi = entry.entry["ortografi"]
                else:
                    ortografi = json.get_path(parent + ["ortografi"], sub_entry)

                if json.has_path(parent + ["homografNr"], sub_entry):
                    homografNr = json.get_path(parent + ["homografNr"], sub_entry)
                else:
                    homografNr = None

                id = Id(namespace, TEXT, TextId(ortografi, homografNr))
                loc = IdLocation(entry, namespace, path, id.format())
                yield id, loc


def parse_refid(kind, ref):
    if kind is None:
        if ref.startswith("lnr"):
            ref = ref[3:]
            kind = LNR
        elif ref.startswith("xnr"):
            ref = ref[3:]
            kind = XNR
        elif ref.startswith("kcnr"):
            ref = ref[4:]
            kind = KCNR
        else:
            kind = UNKNOWN

    return kind, ref


text_xnr_regexp = re.compile(r"(.*)\s+([0-9]+)")
ref_regexp = re.compile(r"(?<=refid=)[a-zA-Z0-9]*")
full_ref_regexp = re.compile(r"\+\w+\(refid=([a-zA-Z0-9]*)\)")


def parse_ref(entry, namespace, path):
    value = json.get_path(path, entry.get(namespace.path, {}))

    match = full_ref_regexp.fullmatch(value)
    if match is None:
        return None

    kind, ref = parse_refid(None, match.group(0))
    return Id(namespace, kind, ref), IdLocation(entry, namespace, path, orig_ref)


def find_text_references(tree_ortografi, tree_homografNr, tree):
    if isinstance(tree, str):
        return

    if isinstance(tree, list):
        for subtree in tree:
            yield from find_text_references(tree_ortografi, tree_homografNr, subtree)
        return

    if tree.tag != "i":
        yield from find_text_references(tree_ortografi, tree_homografNr, tree.contents)
        return

    items = markup_parser.to_markup(tree.contents).split(",")

    for item in items:
        item = item.strip()
        if not item:
            continue
        if ref_regexp.search(item):
            continue
        match markup_parser.parse(item):
            case [markup_parser.Element("sup", sup_contents), *rest]:
                homografNr = int(markup_parser.text_contents(sup_contents))
                ortografi_xnr = markup_parser.text_contents(rest)
            case _:
                homografNr = None
                ortografi_xnr = item

        maybe_match = text_xnr_regexp.search(ortografi_xnr)
        if maybe_match:
            ortografi = maybe_match.group(1)
            lemmaNr = maybe_match.group(2)
        else:
            ortografi = ortografi_xnr
            lemmaNr = None

        # skip discussion of prefixes
        if ortografi.endswith("-") and not homografNr and not lemmaNr:
            continue

        # e.g. starr => [i grön s.]
        if ortografi.endswith(" " + tree_ortografi[0] + "."):
            continue

        # e.g. a reference [i katt] inside 1 katt refers to 1 katt
        if homografNr is None and ortografi == tree_ortografi:
            homografNr = tree_homografNr

        yield markup_parser.to_markup(tree), TextId(ortografi, homografNr)


def find_refs_in_namespace(entry, namespace):
    ortografi = entry.entry["ortografi"]
    body = entry.entry.get(namespace.path, {})
    homografNr = body.get("homografNr")

    for field, orig_kind in ref_fields[namespace].items():
        for path in json.expand_path(field, body):
            orig_ref = json.get_path(path, body)
            kind, ref = parse_refid(orig_kind, orig_ref)
            yield Id(namespace, kind, ref), IdLocation(entry, namespace, path, orig_ref)

    for path in json.all_paths(body):
        field = json.path_str(path, strip_positions=True)
        if field in ref_fields[namespace]:
            continue

        value = json.get_path(path, body)

        if not isinstance(value, str):
            continue

        results = ref_regexp.findall(value)
        for orig_ref in results:
            kind, ref = parse_refid(None, orig_ref)
            yield Id(namespace, kind, ref), IdLocation(entry, namespace, path, orig_ref)

    for field in freetext_fields[namespace]:
        for path in json.expand_path(field, body):
            value = json.get_path(path, body)
            try:
                tree = markup_parser.parse(value)
                for text, ref in find_text_references(ortografi, homografNr, tree):
                    id = Id(namespace, TEXT, ref)
                    yield id, IdLocation(entry, namespace, path, text)
            except lark.LarkError:
                pass  # TODO: generate warning


def find_refs(entry):
    for namespace in [SO, SAOL]:
        yield from find_refs_in_namespace(entry, namespace)


def entry_name(entry, namespace, ref=None):
    if isinstance(ref, Id) and ref.type == TEXT:
        ortografi = ref.id.ortografi
        homografNr = ref.id.homografNr
    else:
        ortografi = entry.entry["ortografi"]
        if namespace is None:
            homografNr = None
        else:
            homografNr = entry.entry.get(namespace.path, {}).get("homografNr")

    if homografNr is None:
        return ortografi
    else:
        return f"{homografNr} {ortografi}"


# Output formats.


def entry_cell(entry: EntryDto, namespace: Namespace, ref: Id | None = None):
    ortografi = entry.entry["ortografi"]
    quoted_query = quote(f"and(equals|ortografi|{ortografi})")
    url = (
        f"https://spraakbanken.gu.se/karp/?mode=salex&lexicon=salex&query={quoted_query}&show=salex:{entry.id}&tab=edit"
    )
    name = entry_name(entry, namespace, ref)

    return link_cell(url=url, text=name)


add_write_via_handler(Namespace, str)
add_write_via_handler(Id, lambda id: id.format())
add_write_via_handler(IdLocation, lambda loc: entry_cell(entry=loc.entry, namespace=loc.namespace))


@dataclass
class IdWithLocation:
    id: Id
    loc: IdLocation


add_write_via_handler(
    IdWithLocation, lambda id_loc: entry_cell(entry=id_loc.loc.entry, namespace=id_loc.loc.namespace, ref=id_loc.id)
)


@dataclass(frozen=True)
class EntryWarning(TestWarning):
    entry: EntryDto
    namespace: Namespace

    def to_dict(self, include_ordbok=True):
        result = {"Ord": entry_cell(self.entry, self.namespace)}
        if include_ordbok and self.namespace is not None:
            result["Ordbok"] = self.namespace
        return result

    def sort_key(self):
        return entry_sort_key(self.entry, self.namespace)


@dataclass(frozen=True)
class FieldWarning(EntryWarning):
    path: str | list[str]
    highlight: str | None

    def to_dict(self, **kwargs):
        if self.namespace is None:
            path = self.path
        else:
            path = [self.namespace.path] + json.make_path(self.path)

        return super().to_dict(**kwargs) | {
            "Fält": json.path_str(self.path, strip_positions=True),
            "Text": highlight(self.highlight, json.get_path(path, self.entry.entry)),
        }


def entry_sort_key(entry, namespace):
    return (entry.entry["ortografi"], entry_name(entry, namespace))


def parse_böjning(entry, namespace, only_alpha=True):
    böjning = entry.entry.get(namespace.path, {}).get("böjning", "")
    match namespace:
        case Namespace.SAOL:
            parts = [f.text.strip() for f in markup_parser.text_fragments(böjning) if not f.tags]
        case Namespace.SO:
            parts = [f.text.strip() for f in markup_parser.text_fragments(böjning) if f.tags == ["i"]]

    if only_alpha:
        parts = [p for p in parts if p and p[0].isalpha()]

    def simplify(p):
        return p.replace("(", "").replace(")", "").replace(",", "").replace(";", "")

    return [simplify(p) for p in parts]


def variant_forms(entry, namespace, include_hidden=False, include_main_form=False):
    for id, loc in text_ids(entry, namespace):
        if not include_hidden and not loc.visible:
            continue

        if include_main_form or id.id.ortografi != entry.entry["ortografi"]:
            yield id.id.ortografi
