"""Utility functions specific to Salex."""

import karp.foundation.json as json
from copy import deepcopy
from enum import Enum, global_enum
from dataclasses import dataclass, field
import re
from karp.lex.domain.dtos import EntryDto


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

        if not test(json.get_path(path, data)):
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
            case Namespace.SO: return "so"
            case Namespace.SAOL: return "saol"


@global_enum
class IdType(Enum):
    LNR = 0
    XNR = 1
    KCNR = 2
    INR = 3
    UNKNOWN = 4

def format_ref(type, id):
    return f"{str(type).lower()}{id}"

@dataclass(frozen=True)
class Id:
    namespace: Namespace
    type: IdType
    id: str

    def format(self):
        return format_ref(self.type, self.id)

@dataclass
class IdLocation:
    entry: EntryDto
    path: list[str]
    text: str

    @property
    def visible(self):
        return is_visible(self.path, self.entry.entry)

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
    },
}


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
        "variantformer.id": LNR,
        # "enbartDigitalaHänvisningar.hänvisning": None, this is in +refid(...) form
        # "huvudbetydelser.hänvisning": None, this is in +refid(...) form
    },
}


def find_ids(entry):
    for namespace in id_fields:
        sub_entry = entry.entry.get(namespace.path, {})
        for field, kind in id_fields[namespace].items():
            for path in json.expand_path(field, sub_entry):
                id = json.get_path(path, sub_entry)
                yield Id(namespace, kind, id), IdLocation(entry, [namespace.path] + path, id)


def parse_ref(kind, ref):
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


ref_regexp = re.compile(r"(?<=refid=)[a-zA-Z0-9]*")


def find_refs_in_namespace(entry, namespace):
    body = entry.entry.get(namespace.path, {})
    for field, orig_kind in ref_fields[namespace].items():
        for path in json.expand_path(field, body):
            orig_ref = json.get_path(path, body)
            kind, ref = parse_ref(orig_kind, orig_ref)
            yield Id(namespace, kind, ref), IdLocation(entry, [namespace.path] + path, orig_ref)

    for path in json.all_paths(body):
        field = json.path_str(path, strip_positions=True)
        if field in ref_fields[namespace]:
            continue

        value = json.get_path(path, body)

        if not isinstance(value, str):
            continue

        results = ref_regexp.findall(value)
        for orig_ref in results:
            kind, ref = parse_ref(None, orig_ref)
            yield Id(namespace, kind, ref), IdLocation(entry, [namespace.path] + path, orig_ref)


def find_refs(entry):
    for namespace in [SO, SAOL]:
        yield from find_refs_in_namespace(entry, namespace)


def entry_name(entry, namespace):
    ortografi = entry.entry["ortografi"]
    homografNr = entry.entry.get(namespace.path, {}).get("homografNr")

    if homografNr is None:
        return ortografi
    else:
        return f'{homografNr} {ortografi}'
