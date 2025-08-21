from utils.salex import SAOL, EntryWarning, visible_part
from dataclasses import dataclass
from karp.foundation import json
from tqdm import tqdm


@dataclass(frozen=True)
class EmptyEntryWarning(EntryWarning):
    present: list[str]

    def category(self):
        return f"Tomma ingångar ({self.namespace})"

    def to_dict(self):
        result = super().to_dict()
        if self.present:
            result["Info"] = ", ".join(self.present) + " finns"
        return result


def test_empty_entries(entries):
    for entry in tqdm(entries, desc="Finding empty entries"):
        body = visible_part(entry.entry)

        for path in json.expand_path("saol.huvudbetydelser", body):
            huvudbetydelse = json.get_path(path, body)

            should_have = {"definition", "exempel", "hänvisningar", "bruklighetskommentar", "formkommentar.text"}

            for field in should_have:
                if list(json.expand_path(field, huvudbetydelse)):
                    break
            else:
                yield EmptyEntryWarning(entry, SAOL, [])
