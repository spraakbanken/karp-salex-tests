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
        inflected_forms = list(inflection.inflected_forms(entry, tag=True))
        inflection_table = {tag: form for tag, form in inflected_forms}
        if not inflection_table: continue

        try:
            form = inflection_table.get("V0N0A") or inflection_table["V0N0D"]
        except:
            form = inflected_forms[0][1]

        if word != form:
            yield InflectionWarning(entry, SAOL, form)
