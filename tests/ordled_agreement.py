from utils.salex import SAOL, EntryWarning
from dataclasses import dataclass

@dataclass(frozen=True)
class OrdledWarning(EntryWarning):
    ordled: str

    def category(self):
        return f"Felaktiga ordled ({self.namespace})"

    def to_dict(self):
        return super().to_dict() | {"Ordled": self.ordled}

def test_ordled_agreement(entries):
    for entry in entries:
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
