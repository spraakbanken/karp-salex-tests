from utils.salex import EntryWarning, SAOL, visible_part
from tqdm import tqdm
from dataclasses import dataclass


@dataclass(frozen=True)
class InflectionWarning(EntryWarning):
    first_form: str

    def collection(self):
        return "Extra"

    def category(self):
        return f"Första böjningsform ({self.namespace})"

    def to_dict(self):
        return super().to_dict(include_ordbok=False) | {
            "Första böjningsform": self.first_form,
            "Ordklass": self.entry.entry["ordklass"],
        }


def test_böjningar_first(inflection, entries):
    for entry in tqdm(entries, desc="Checking first inflected forms"):
        entry = visible_part(entry)
        if "saol" not in entry.entry: continue

        word = entry.entry.get("ortografi")
        inflection_table = list(inflection.inflected_forms(entry))
        if not inflection_table: continue
        form = inflection_table[0]

        if word != form:
            yield InflectionWarning(entry, SAOL, form)
