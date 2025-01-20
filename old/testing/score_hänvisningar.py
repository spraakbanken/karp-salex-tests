from karp.foundation import json
from collections import defaultdict, Counter
import pickle
from enum import Enum, global_enum
import re
from karp.lex.domain.dtos import EntryDto
import csv
import sys

# import fasttext
import gensim


def similarity(v1, v2):
    return dot(v1, v2) / (magnitude(v1) * magnitude(v2) + 0.000001)


def magnitude(v):
    return sum(x**2 for x in v) ** 0.5


def dot(v1, v2):
    return sum(x * y for x, y in zip(v1, v2))


@global_enum
class Id(Enum):
    ID = 0
    LNR = 1
    XNR = 2
    KCNR = 3
    INR = 4
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

keys = defaultdict(dict)
key_ids = defaultdict(dict)
key_variant = defaultdict(dict)
entries_by_id = {}
references = []


def add(entry, kind, key, visas):
    variant = entry.entry.get("saol", {}).get("variant", False)
    if key in keys[kind] and entry.id != key_ids[kind].get(key):
        pass
    else:
        keys[kind][key] = visas or keys[kind].get(key, False)
        key_ids[kind][key] = entry.id
        key_variant[kind][key] = variant


def visas(path, entry):
    # breakpoint()
    # print("checking visas", path)
    for i in range(len(path) + 1):
        visas_path = path[:i] + ["visas"]
        if json.has_path(visas_path, entry.entry) and not json.get_path(visas_path, entry.entry):
            return False

    return True


entries = list(entry_queries.all_entries("salex", expand_plugins=False))
# with open("entries.pickle", "rb") as file:
#    entries = pickle.load(file)


# add keys
for entry in entries:
    entries_by_id[entry.id] = entry
    for field, kind in id_fields.items():
        for path in json.expand_path(field, entry.entry):
            add(entry, kind, json.get_path(path, entry.entry), visas(path, entry))

    ortografi = entry.entry.get("ortografi")


def check_ref(entry, path, kind, ref):
    ortografi = entry.entry.get("ortografi")
    if not ortografi:
        return
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
            return

    if keys[kind].get(ref):
        sub_ortografi = entries_by_id[key_ids[kind][ref]].entry.get("ortografi")
        if sub_ortografi:
            references.append((ortografi, sub_ortografi))


for entry in entries:
    for field, kind in ref_fields.items():
        for path in json.expand_path(field, entry.entry):
            if not visas(path, entry):
                continue
            ref = json.get_path(path, entry.entry)

            check_ref(entry, path, kind, ref)

    # check plain text references
    for path in json.all_paths(entry.entry):
        if not visas(path, entry):
            continue
        field = json.path_str(path)
        if field in ref_fields:
            continue
        if path and path[0] in ["so", "saol"]:
            value = json.get_path(path, entry.entry)

            if not isinstance(value, str):
                continue
            results1 = re.findall(r"(?<=refid=)[a-zA-Z0-9]*", value)
            for ref in results1:
                check_ref(entry, path, None, ref)

print(len(references))

# model = fasttext.load_model("cc.sv.300.bin")
model = gensim.models.fasttext.FastText.load("kubord-fasttext-gp-2013-2022-token.bin")


def word_similarity(w1, w2):
    v1 = model.wv.get_vector(w1).tolist()
    v2 = model.wv.get_vector(w2).tolist()
    return similarity(v1, v2)


reference_scores = [(x, y, word_similarity(x, y)) for x, y in references]
reference_scores.sort(key=lambda tup: tup[2])
for x, y, score in reference_scores:
    print(x, "/", y, "=", score)

exit()
