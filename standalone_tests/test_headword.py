import json
from collections import defaultdict
from frozendict import deepfreeze


def sep(*args, separator=" "):
    return separator.join(str(x) for x in args if x is not None)


def entry_name(entry):
    homografNr = entry.get("homografNr")
    return sep(homografNr, entry["ortografi"])


def abstract(entry):
    variantformer = entry.get("variantformer", [])

    def many(x):
        lst = list(x)
        return (any(lst), len(list(x for x in lst if x)) > 1, any(lst) and all(lst))

    return {
        # "has_homografNr": "homografNr" in entry,
        "uppdelas": entry.get("uppdelas", False),
        "böjning": bool(entry.get("böjning")),
        "ordled": bool(entry.get("ordled")),
        "variantformer": bool(variantformer),
        "flera_variantformer": len(variantformer) > 1,
        "variantformer_uttal": many("uttal" in x for x in variantformer),
        "variantformer_böjning": many("böjning" in x for x in variantformer),
        "variantformer_ordled": many("ordled" in x for x in variantformer),
        "variantformer_uppdelas": many(x.get("uppdelas", False) for x in variantformer),
    }


groups = defaultdict(list)

for line in open("/home/nick/prog/sb/export-stuff/saol_tryckt_250825.jsonl", "r"):
    #    entry = visible_part(json.loads(line), test=entry_is_visible_in_printed_book)
    entry = json.loads(line)
    if entry["ingångstyp"] == "variant":
        continue

    abstracted = abstract(entry)
    groups[deepfreeze(abstracted)].append(entry)

entries_of_interest = {
    "akne",
    "vanilj",
    "rullad",
    "kex",
    "riksha",
    "rakit",
    "stopplikt",
    "rhododendron",
    "kollektiv",
    "gigawattimme",
    "riksha",
}

for abstracted, entries in sorted(groups.items(), key=lambda x: x[1][0]["ortografi"].lower()):
    print(f"{abstracted}: ({len(entries)})")
    print(entry_name(entries[0]))
    # for e in entries:
    #    if e["ortografi"] in entries_of_interest:
    #        print("***", entry_name(e))
    print()


def values(key):
    return {group[key] for group in groups}


for key in next(iter(groups)).keys():
    print(key, values(key))
