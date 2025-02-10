"""Utility functions specific to Salex."""

import karp.foundation.json as json
from copy import deepcopy
from enum import Enum, global_enum
from dataclasses import dataclass
import re


def entry_is_visible(entry):
    return entry.get("visas", True)


def entry_is_visible_in_printed_book(entry):
    return entry_is_visible(entry) and not entry.get("endastDigitalt", False)


def is_visible(path, entry, test=entry_is_visible):
    path = json.make_path(path)
    for i in range(len(path) + 1):
        if not test(json.get_path(path[:i], entry)):
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


@dataclass
class Id:
    namespace: Namespace
    type: IdType
    id: str

    path: list[str]
    text: str


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
        "variantformer.id": LNR,
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
        # "enbartDigitalaHänvisningar.hänvisning": None, this is in +refid(...) form
        # "huvudbetydelser.hänvisning": None, this is in +refid(...) form
    },
}


def find_ids(entry):
    for namespace in id_fields:
        sub_entry = entry.get(namespace.path(), {})
        for field, kind in id_fields[namespace].items():
            for path in json.expand_path(field, sub_entry):
                id = json.get_path(path, sub_entry)
                yield Id(namespace, kind, id, path, id)


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
    for field, kind in ref_fields[namespace].items():
        for path in json.expand_path(field, entry):
            orig_ref = json.get_path(path, entry)
            kind, ref = parse_ref(path, kind, orig_ref)
            yield Id(namespace, kind, ref, path, orig_ref)

    for path in json.all_paths(entry):
        field = json.path_str(path)
        if field in ref_fields[namespace]:
            continue

        value = json.get_path(path, entry)

        if not isinstance(value, str):
            continue

        results = ref_regexp.findall(value)
        for orig_ref in results:
            kind, ref = parse_ref(path, None, ref)
            yield Id(namespace, kind, ref, path, orig_ref)


def find_refs(entry):
    yield from find_refs_in_namespace(entry.get("so", {}), SO)
    yield from find_refs_in_namespace(entry.get("saol", {}), SAOL)


def entry_name(entry, namespace):
    ortografi = entry.entry["ortografi"]
    match namespace:
        case Namespace.SO: homografNr = entry.entry.get("so", {}).get("homografNr")
        case Namespace.SAOL: homografNr = entry.entry.get("saol", {}).get("homografNr")

    if homografNr is None:
        return ortografi
    else:
        return f'{homografNr} {ortografi}'
