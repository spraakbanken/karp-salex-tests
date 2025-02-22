from karp.foundation import json
import pickle

resource_config = resource_queries.by_resource_id("salex").config
with open("entries.pickle", "rb") as file:
    new_entries = pickle.load(file)
# new_entries = list(entry_queries.all_entries("salex", expand_plugins=False))
with open("old-entries.pickle", "rb") as file:
    old_entries = pickle.load(file)

new_entries = {entry.id: entry for entry in new_entries}
old_entries = {entry.id: entry for entry in old_entries}


def get_path_maybe(field, data):
    for path in json.expand_path(field, data):
        return json.get_path(path, data)


# entry_commands.start_transaction()
for id, entry in new_entries.items():
    if id not in old_entries:
        print(f"MISSING {id} {entry.get('ortografi')}")
        continue

    old_entry = old_entries[id]

    if "so" in entry.entry:
        so_lemma = entry.entry["so"]

        l_nr = so_lemma.get("l_nr")
        if not l_nr:
            print(f"MISSING_LNR {id} {entry.entry.get('ortografi')}")
            continue

        if len(old_entry.entry.get("SOLemman", [])) != 1:
            print(f"WRONG_LENGTH {id} {entry.entry.get('ortografi')}")
            continue

        old_so_lemma = old_entry.entry["SOLemman"][0]

        if old_so_lemma.get("l_nr") != l_nr:
            print(f"WRONG_LNR {id} {entry.entry.get('ortografi')}")

        if get_path_maybe("lexem.x_nr", so_lemma) != get_path_maybe("lexem.x_nr", old_so_lemma):
            print(f"WRONG_XNR {id} {entry.entry.get('ortografi')}")
            so_lemma = entry.entry["so"]

            for lexem, old_lexem in zip(so_lemma.get("lexem", []), old_so_lemma.get("lexem", [])):
                x_nr = lexem.get("x_nr")
                old_x_nr = old_lexem.get("x_nr")
                if not old_x_nr:
                    continue
                lexem["x_nr"] = old_x_nr
            # entry_commands.update_entry("salex", id, entry.version, "", "", entry.entry)

        if get_path_maybe("lexem.cykler.kc_nr", so_lemma) != get_path_maybe("lexem.cykler.kc_nr", old_so_lemma):
            print(f"WRONG_KCNR {id} {entry.entry.get('ortografi')}")

# entry_commands.commit()
exit()
