from karp.foundation import json
from collections import defaultdict, Counter
import pickle
from enum import Enum, global_enum
import re
from karp.lex.domain.dtos import EntryDto
import csv
import sys


@global_enum
class Id(Enum):
    ID = 0
    LNR = 1
    XNR = 2
    KCNR = 3
    INR = 4
    SO_ORTOGRAFI_HOMOGRAFNR = 5
    SAOL_ORTOGRAFI_HOMOGRAFNR = 6
    SAOL_LNR = 7
    SAOL_XNR = 8


id_fields = {
    "so.l_nr": LNR,
    "so.varianter.l_nr": LNR,
    "so.vnomen.l_nr": LNR,
    "so.förkortningar.l_nr": LNR,
    #    "so.lemmaReferenser.l_nr": LNR,
    "so.huvudbetydelser.x_nr": XNR,
    "so.huvudbetydelser.underbetydelser.kc_nr": KCNR,
    "so.huvudbetydelser.idiom.i_nr": INR,
    "saol.id": SAOL_LNR,
    "saol.alt.id": SAOL_LNR,
    "saol.huvudbetydelser.id": SAOL_XNR,
}

ref_fields = {
    "so.huvudbetydelser.hänvisningar.hänvisning": None,
    "so.huvudbetydelser.morfex.hänvisning": None,
    "so.huvudbetydelser.underbetydelser.hänvisningar.hänvisning": None,
    "so.huvudbetydelser.underbetydelser.morfex.hänvisning": None,
    "so.lexem.idiom.hänvisning": INR,
    "so.vnomen.hänvisning": None,
    # "so.relaterade_verb.refid": LNR,
    "saol.moderverb": SAOL_LNR,
}

ortografi_homografnr_fields = {
    "so": SO_ORTOGRAFI_HOMOGRAFNR,
    "so.varianter": SO_ORTOGRAFI_HOMOGRAFNR,
    # "so.vnomen": SO_ORTOGRAFI_HOMOGRAFNR,
    "so.förkortningar": SO_ORTOGRAFI_HOMOGRAFNR,
    "saol": SAOL_ORTOGRAFI_HOMOGRAFNR,
    "saol.alt": SAOL_ORTOGRAFI_HOMOGRAFNR,
}

keys = defaultdict(dict)
key_ids = defaultdict(dict)
key_variant = defaultdict(dict)
comments = defaultdict(dict)


def add(entry, kind, key, visas):
    variant = entry.entry.get("saol", {}).get("variant", False)
    lnr = json.get_path("so.l_nr", entry.entry) if json.has_path("so.l_nr", entry.entry) else None
    if key in keys[kind] and entry.id != key_ids[kind].get(key):
        if variant or key_variant[kind].get(key):
            warn("duplicate", entry, [], kind, key)
    else:
        keys[kind][key] = visas or keys[kind].get(key, False)
        key_ids[kind][key] = entry.id
        key_variant[kind][key] = variant
        comments[kind][key] = [entry.entry.get("ortografi", ""), kind]


def visas(path, entry):
    # breakpoint()
    # print("checking visas", path)
    for i in range(len(path) + 1):
        visas_path = path[:i] + ["visas"]
        if json.has_path(visas_path, entry.entry) and not json.get_path(visas_path, entry.entry):
            return False

    return True


writer = csv.writer(sys.stdout)


def warn(category, entry, path, kind, ref):
    if path[0] == "so":
        lnr = json.get_path("so.l_nr", entry.entry) if json.has_path("so.l_nr", entry.entry) else None
    elif path[0] == "saol":
        lnr = json.get_path("saol.id", entry.entry) if json.has_path("saol.id", entry.entry) else None
    else:
        assert False
    status = "visas" if visas(path, entry) else "förråd"
    field = json.path_str([x for x in json.make_path(path) if isinstance(x, str)])  # json.path_str(path)
    # print(f'{category} {status} {lnr} {entry.entry.get("ortografi")} {field} {kind} {ref}')
    writer.writerow(
        [category, status, lnr, entry.entry.get("ortografi"), field, kind, ref] + comments[kind].get(ref, [])
    )


# import json as js
# entry = EntryDto(**js.loads(r"""{
#  "id": "01HKQFKKWKHQ3G725DPWGRFG5V",
#  "version": 1,
#  "lastModified": 1729755079.552054,
#  "lastModifiedBy": "local admin",
#  "message": "Entry updated",
#  "discarded": false,
#  "resource": "salex",
#  "entry": {
#    "id": "01HC2YF33YX3D42YXRS2YVTA6K",
#    "ortografi": "antropo-",
#    "ordklass": "förled",
#    "böjningsklass": "85a",
#    "sorteringsform": "antropo",
#    "so": {
#      "visas": true,
#      "l_nr": "105835",
#      "uttal": [
#        {
#          "visas": true,
#          "filnamnInlästUttal": "105835_1.mp3"
#        }
#      ],
#      "huvudbetydelser": [
#        {
#          "x_nr": "105836",
#          "definition": "som rör +människan(refid=xnr251963)",
#          "hänvisningar": [
#            {
#              "typ": "SYN:synonym",
#              "hänvisning": "lnr3004301",
#              "visas": false
#            }
#          ],
#          "morfex": [
#            {
#              "ortografi": "antropoid",
#              "visas": true
#            },
#            {
#              "ortografi": "antropomorf",
#              "visas": true,
#              "hänvisning": "lnr105855"
#            }
#          ],
#          "visas": true,
#          "etymologi": {
#            "förstaBelägg": "sedan ca 1720",
#            "beskrivning": "till grek. [i an´thropos] 'människa'",
#            "visas": true
#          }
#        }
#      ]
#    }
#  }
# }
# """))
# print(visas(["so", "huvudbetydelser", 0, "hänvisningar", 0, "hänvisning"], entry))
# exit()

entries = list(entry_queries.all_entries("salex", expand_plugins=False))
# with open("entries.pickle", "rb") as file:
#    entries = pickle.load(file)


# add keys
for entry in entries:
    for field, kind in id_fields.items():
        for path in json.expand_path(field, entry.entry):
            add(entry, kind, json.get_path(path, entry.entry), visas(path, entry))

    ortografi = entry.entry.get("ortografi")
    for field, kind in ortografi_homografnr_fields.items():
        for path in json.expand_path(field, entry.entry):
            # print(entry.id, field, path, entry.entry)
            if not visas(path, entry):
                continue

            value = json.get_path(path, entry.entry)
            sub_ortografi = value.get("ortografi") or ortografi
            sub_hnr = value.get("homografNr")
            # print("adding", kind, path)
            add(entry, kind, (sub_ortografi, sub_hnr), True)

# check missing homografNr
for kind in [SO_ORTOGRAFI_HOMOGRAFNR, SAOL_ORTOGRAFI_HOMOGRAFNR]:
    for ort, hnr in keys[kind]:
        if hnr is not None and (ort, None) in keys[kind]:
            if keys[kind][ort, hnr] and keys[kind][ort, None]:
                print(f"missing_hnr {kind} {ort} {hnr}")

# exceptions
exceptions = defaultdict(set)
for key in open("bojform_id", "r").readlines():
    key = key.strip()
    exceptions[LNR].add(key)
for key in open("bojformer_bojform_id", "r").readlines():
    key = key.strip()
    exceptions[LNR].add(key)


def check_ref(entry, path, kind, ref):
    field = json.path_str(path)
    saol = field.startswith("saol.")
    if not kind:
        if ref.startswith("lnr"):
            ref = ref[3:]
            kind = SAOL_LNR if saol else LNR
        elif ref.startswith("kcnr"):
            ref = ref[4:]
            kind = KCNR
        elif ref.startswith("xnr"):
            ref = ref[3:]
            kind = SAOL_XNR if saol else XNR
        else:
            warn("unknown", entry, path, kind, ref)
            return

    if ref not in keys[kind]:
        if ref in exceptions[kind]:
            warn("exception", entry, path, kind, ref)

        elif len(ref) >= 4 and all(c == "9" for c in ref):
            warn("dummy", entry, path, kind, ref)
        else:
            warn("missing", entry, path, kind, ref)
    elif not keys[kind][ref]:
        warn("förråd", entry, path, kind, ref)


for entry in entries:
    for field, kind in ref_fields.items():
        for path in json.expand_path(field, entry.entry):
            # if not visas(path, entry): continue
            ref = json.get_path(path, entry.entry)

            check_ref(entry, path, kind, ref)

    # check plain text references
    for path in json.all_paths(entry.entry):
        # if not visas(path, entry): continue
        field = json.path_str(path)
        if field in ref_fields:
            continue
        if path and path[0] in ["so", "saol"]:
            value = json.get_path(path, entry.entry)

            if not isinstance(value, str):
                continue
            results1 = re.findall(r"(?<=refid=)[a-zA-Z0-9]*", value)
            results2 = re.findall(r"(?:x|l|kc)nr[a-zA-Z0-9]+", value)
            for ref in results1:
                check_ref(entry, path, None, ref)

            extra = set(results2) - set(results1)
            if extra and "hänvisning" not in path:
                warn("non_standard_reference", entry, path, kind, ref)

# exit()
