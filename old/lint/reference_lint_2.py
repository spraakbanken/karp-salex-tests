from karp.foundation import json
from collections import defaultdict, Counter
import pickle
from dataclasses import dataclass
from enum import Enum, global_enum
import re
import tqdm
from karp.plugins.plugin import untransform_entry
import itertools

resource_config_old = resource_queries.by_resource_id("salex_pre_update").config
resource_config_new = resource_queries.by_resource_id("salex").config

files = {}


def warn(kind, entry, *args):
    if kind not in files:
        files[kind] = open(f"lint-warnings-2/{kind}.txt", "w")

    msg = f"{entry.id} ({entry.entry.get('ortografi')}): " + " ".join(map(str, args))
    print(msg, file=files[kind])
    print(kind + ":", msg)


@global_enum
class Id(Enum):
    ID = 0
    LNR = 1
    XNR = 2
    KCNR = 3
    ORTOGRAFI_HOMOGRAFNR = 4


new_id_fields = {
    "saol.id": LNR,
    # "saol.alt.id": LNR,
    "saol.huvudbetydelser.id": XNR,
}

old_id_fields = {
    "SAOLLemman.id": LNR,
    "SAOLLemman.lexem.id": XNR,
}

new_ref_fields = {
    # "saol.hänvisningar.hänvisning": None,
    # "saol.huvudbetydelser.hänvisningar.hänvisning": None,
    # "saol.moderverb": LNR,
}

old_ref_fields = {
    # "SAOLLemman.hänvisningar.hänvisning": None,
    # "SAOLLemman.lexem.hänvisningar.hänvisning": None,
}


def ids(entry, fields):
    result = set()
    for field, kind in fields.items():
        for path in json.expand_path(field, entry.entry):
            value = json.get_path(path, entry.entry)
            if field == "SAOLLemman.lexem.id" and value.startswith("xnr"):
                value = value[3:]
            result.add((kind, value))

    return result


def refs(entry, fields, entries):
    result = {}
    field = None

    def add_ref(kind, ref):
        nonlocal result

        if not kind:
            if ref.startswith("lnr"):
                ref = ref[3:]
                kind = LNR
            elif ref.startswith("kcnr"):
                ref = ref[4:]
                kind = KCNR
            elif ref.startswith("xnr"):
                ref = ref[3:]
                kind = XNR
            else:
                warn("unknown_reference", entry, f"unknown reference {ref} in field {field}")
                result[("unknown", ref)] = ("unknown", ref)
                return

        target_entry = entries[kind].get(ref)
        if target_entry:
            result[target_entry.id] = (kind, ref)
        elif kind != ORTOGRAFI_HOMOGRAFNR:  # missing ORTOGRAFI_HOMOGRAFNR should not be linked
            warn("broken_link", entry, f"broken link {kind} {ref} in field {field}")
            result[(kind, ref)] = (kind, ref)

    for field, kind in fields.items():
        for path in json.expand_path(field, entry.entry):
            add_ref(kind, json.get_path(path, entry.entry))

    # add vnomen and morfex for old entries
    if entries.old:
        for path in json.expand_path("SOLemman.lemmaReferenser", entry.entry):
            value = json.get_path(path, entry.entry)
            if value.get("lemmatyp") == "vnomen" and value.get("länkas") == True:
                homografNr = value.get("homografNr")
                ortografi = value.get("ortografi")
                add_ref(ORTOGRAFI_HOMOGRAFNR, (ortografi, homografNr))
        for path in json.expand_path("SOLemman.lexem", entry.entry):
            lexem = json.get_path(path, entry.entry)
            if lexem.get("visas") == False:
                continue
            for value in lexem.get("morfex", []):
                if value.get("visas") == False:
                    continue
                homografNr = value.get("homografNr")
                ortografi = value.get("ortografi")
                add_ref(ORTOGRAFI_HOMOGRAFNR, (ortografi, homografNr))
        for path in json.expand_path("SOLemman.lexem.cykler", entry.entry):
            cykel = json.get_path(path, entry.entry)
            if cykel.get("visas") == False:
                continue
            for value in cykel.get("morfex", []):
                if value.get("visas") == False:
                    continue
                homografNr = value.get("homografNr")
                ortografi = value.get("ortografi")
                add_ref(ORTOGRAFI_HOMOGRAFNR, (ortografi, homografNr))

    # check plain text references
    for path in json.all_paths(entry.entry):
        if path and (path[0] in ["so", "SOLemman"]):
            value = json.get_path(path, entry.entry)

            if not isinstance(value, str):
                continue
            results1 = re.findall(r"(?<=refid=)[a-zA-Z0-9]*", value)
            results2 = re.findall(r"(?:x|l|kc)nr[a-zA-Z0-9]+", value)
            for ref in results1:
                add_ref(None, ref)

            extra = set(results2) - set(results1)
            if extra and "hänvisning" not in path:
                warn("non_standard_reference", entry, path, extra)

    return result


class Entries:
    def __init__(self, old=False):
        self._by_key = {x: {} for x in Id}
        self.old = old

    def __getitem__(self, key):
        return self._by_key[key]

    def __iter__(self):
        return iter(self[ID].values())

    def _add_key(self, id, key, entry):
        if key in self[id]:
            if id != ORTOGRAFI_HOMOGRAFNR:
                warn("duplicate_key", entry, f"duplicate {id} {key} - already taken by {self[id][key].id}")
        else:
            self[id][key] = entry

    def add(self, entry):
        self._add_key(ID, entry.id, entry)
        processed = set()

        keys = set()
        fields = old_id_fields if self.old else new_id_fields
        for field, id in fields.items():
            for path in json.expand_path(field, entry.entry):
                key = json.get_path(path, entry.entry)
                keys.add((id, key))

        for id, key in keys:
            self._add_key(id, key, entry)

        lemma_field = "SOLemman" if self.old else "so"
        for path in json.expand_path(lemma_field, entry.entry):
            value = json.get_path(path, entry.entry)
            if value.get("visas") == False:
                continue
            ortografi = value.get("ortografi")
            homografNr = value.get("homografNr")
            self._add_key(ORTOGRAFI_HOMOGRAFNR, (ortografi, homografNr), entry)


new_entries = Entries(old=False)
old_entries = Entries(old=True)

# for entry in itertools.islice(tqdm.tqdm(entry_queries.all_entries('salex', expand_plugins=False)), 100000, 102000):
# for entry in tqdm.tqdm(entry_queries.all_entries("salex", expand_plugins=False)):
#    new_entries.add(entry, old=False)
#
#    if "so" not in entry.entry:
#        continue
#
#    # find old entry
#    for version in reversed(range(entry.version)):
#        old_entry = entry_queries.get_entry_history("salex", entry.id, version, expand_plugins=False)
#        if "SOLemman" in old_entry.entry:
#            old_entries.add(old_entry, old=True)
#            break
#    else:
#        warn(entry, "couldn't find old version")

for entry in entry_queries.all_entries("salex", expand_plugins=False):
    new_entries.add(entry)
for entry in entry_queries.all_entries("salex_pre_update", expand_plugins=False):
    old_entries.add(entry)
# with open("entries.pickle", "rb") as file:
#    for entry in pickle.load(file):
#        new_entries.add(entry)

# with open("old-entries.pickle", "rb") as file:
#    for entry in pickle.load(file):
#        old_entries.add(entry)

# kc_xnr = {}
# for entry in old_entries[ID].values():
#    for path in json.expand_path("SOLemman.lexem", entry.entry):
#        lexem = json.get_path(path, entry.entry)
#        kc_nr = lexem.get("kc_nr")
#        x_nr = lexem.get("x_nr")
#        if kc_nr and x_nr:
#            if kc_nr in kc_xnr:
#                warn("duplicate_kc_nr", entry)
#            else:
#                kc_xnr[kc_nr] = x_nr

print("Statistics:")
for id in Id:
    print(str(id), len(new_entries[id]))
print()


def check_entry_id_numbers():
    """check that entry ID numbers are OK"""

    for entry in new_entries:
        old_entry = old_entries[ID].get(entry.id)
        if not old_entry:
            warn("old_entry_not_found", entry)
            continue

        new_ids = ids(entry, new_id_fields)
        old_ids = ids(old_entry, old_id_fields)

        only_new = new_ids - old_ids
        only_old = old_ids - new_ids

        if only_new:
            warn("id_number", entry, f"extra ids {only_new}")

        if only_old:
            warn("id_number", entry, f"missing ids {only_old}")


def check_references():
    """check that entry references are OK"""

    for entry in new_entries:
        old_entry = old_entries[ID].get(entry.id)
        if not old_entry:
            warn("old_entry_not_found", entry)
            continue

        new_refs = refs(entry, new_ref_fields, new_entries)
        old_refs = refs(old_entry, old_ref_fields, old_entries)

        only_new = {id: ref for id, ref in new_refs.items() if id not in old_refs}
        only_old = {id: ref for id, ref in old_refs.items() if id not in new_refs}

        replacements = {}
        for key, value in dict(only_new).items():
            if key == value and key in only_old.values():  # same reference but no longer present
                actual_key = [k for k in only_old if only_old[k] == key][0]
                replacements[key] = actual_key

                del only_new[key]
                del only_old[actual_key]

        if all(kind == "unknown" for kind, _ in only_old.values()) and len(only_old) == len(only_new):
            continue

        if only_new and only_old:
            category = "different_refs"
        elif only_new:
            category = "extra_refs"
        elif only_old:
            category = "missing_refs"

        if only_new:
            warn(category, entry, f"extra refs {only_new}")

        if only_old:
            warn(category, entry, f"missing refs {only_old}")


def main():
    check_entry_id_numbers()
    check_references()
    for file in files.values():
        file.close()


if __name__ in ["__main__", "builtins"]:
    main()
    exit()
