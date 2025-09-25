import json
import re
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class Ref:
    typ: str
    id: str
    ortografi: str
    homografNr: int | None
    huvudbetydelseNr: int | None


ref_re = re.compile(r"\[href ([a-zA-Z0-9]*)")


def sep(*args, separator=" "):
    return separator.join(str(x) for x in args if x is not None)


def entry_name(entry):
    homografNr = entry.get("saol", {}).get("homografNr")
    return sep(homografNr, entry["ortografi"])


class IdGenerator:
    def __init__(self, letters=None):
        self.next_id = 0
        self.letters = letters

    def fresh_id(self):
        result = self.next_id
        self.next_id += 1
        if self.letters:
            return self.letters[result]
        else:
            return result

    def __call__(self):
        return self.fresh_id()


def abstract_types(refs):
    letters = ["A", "B", "C", "D", "E", "F", "G", "H"]
    numbers = ["i", "j", "k", "l"]

    seen_ortografi = defaultdict(IdGenerator(letters))
    seen_homografer = defaultdict(lambda: defaultdict(IdGenerator(numbers)))

    # To make the output prettier, only include the homografNr if
    # there is more than one homograf
    for ref in refs:
        id_ortografi = seen_ortografi[ref.ortografi]
        id_homograf = seen_homografer[ref.ortografi][ref.homografNr]
    for dict in seen_homografer.values():
        if len(dict) == 1:
            dict[next(iter(dict))] = ""

    result = []
    for ref in refs:
        result.append(ref.typ)
        id_ortografi = seen_ortografi[ref.ortografi]
        id_homograf = seen_homografer[ref.ortografi][ref.homografNr]
        result.append(id_homograf + id_ortografi)

    return " ".join(result)


interest_groups = {"till A till B", "till iA , jA", "till A , B", "till A el. B"}
groups = defaultdict(list)
wrong_order = []

for line in open("/home/nick/prog/sb/export-stuff/salex_digi_250825.jsonl", "r"):
    entry = json.loads(line)
    saol = entry.get("saol")
    if not saol:
        continue
    if saol.get("endastDigitalt", False):
        continue
    info = saol.get("_hänvisning_info")
    if not info:
        continue
    info_dict = {hv["id"]: hv for hv in info}

    for hb in saol.get("huvudbetydelser", []):
        if saol.get("endastDigitalt", False):
            continue
        hvs = hb.get("hänvisningar")
        if not hvs:
            continue

        refs = []
        for hv in hvs:
            match = ref_re.match(hv["hänvisning"])
            id = match.group(1)
            hv_info = info_dict[id]
            refs.append(
                Ref(hv["typ"], id, hv_info["ortografi"], hv_info["homografNr"], hv_info.get("huvudbetydelseNr"))
            )

        # check for assyriska problem
        for ref1, ref2 in zip(refs, refs[1:]):
            same_types = ref1.typ == ref2.typ or ref2.typ in [",", "och"]
            if (
                same_types
                and ref1.homografNr == ref2.homografNr
                and ref1.ortografi == ref2.ortografi
                and ref1.huvudbetydelseNr >= ref2.huvudbetydelseNr
            ):
                wrong_order.append(entry)
            elif (
                same_types
                and ref1.ortografi == ref2.ortografi
                and ref1.huvudbetydelseNr == ref2.huvudbetydelseNr
                and ref1.homografNr >= ref2.homografNr
            ):
                wrong_order.append(entry)

        types = abstract_types(refs)
        groups[types].append((entry, refs))

if wrong_order:
    print("Wrong order:")
    for entry in wrong_order:
        print("  " + entry_name(entry))
    print()

for types, entries in sorted(groups.items(), key=lambda x: x[1][0][0]["ortografi"]):
    print(f"{types}: ({len(entries)})")
    for entry, refs in entries:
        print(entry_name(entry), end=": ")
        ref_strs = []
        for ref in refs:
            ref_strs.append(sep(ref.typ, ref.homografNr, ref.ortografi, ref.huvudbetydelseNr))
        print(" / ".join(ref_strs))
        if types not in interest_groups:
            break

    print()
