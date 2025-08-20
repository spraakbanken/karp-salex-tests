from utils.salex import SAOL, EntryWarning
from dataclasses import dataclass
from tqdm import tqdm


@dataclass(frozen=True)
class OrdledWarning(EntryWarning):
    ordled: str

    def category(self):
        return f"Felaktiga ordled ({self.namespace})"

    def to_dict(self):
        return super().to_dict() | {"Ordled": self.ordled}


def test_ordled_agreement(entries):
    for entry in tqdm(entries, desc="Checking ordled agreement"):
        ortografi = entry.entry.get("ortografi")
        ordled = entry.entry.get("saol", {}).get("ordled")

        replacements = {
            "·": "",
            "|": "",
            "bbb": "bb",
            "ttt": "tt",
            "sss": "ss",
            "lll": "ll",
            "rrr": "rr",
            "fff": "ff",
            "ppp": "pp",
            "ddd": "dd",
            "ggg": "gg",
            "nnn": "nn",
            "mmm": "mm",
        }

        if ortografi and ordled:
            squashed_ordled = ordled

            for k, v in replacements.items():
                squashed_ordled = squashed_ordled.replace(k, v)

            if ortografi != squashed_ordled:
                yield OrdledWarning(entry, SAOL, ordled)

def test_ordled_format(entries):
    for entry in tqdm(entries, desc="Checking ordled format"):
        ordled = entry.entry.get("saol", {}).get("ordled")
        if not ordled: continue

        if ordled.startswith("·") or ordled.startswith("|") or ordled.endswith("·") or ordled.endswith("|") or "··" in ordled or "." in ordled:
            yield OrdledWarning(entry, SAOL, ordled)
