from tqdm import tqdm
from utils.salex import visible_part, EntryWarning, SO, ref_regexp
from utils.testing import markup_cell
from dataclasses import dataclass
from karp.foundation import json


@dataclass(frozen=True)
class SOTooManyReferences(EntryWarning):
    field: str
    value: str

    def collection(self):
        return "SO"

    def category(self):
        return "Många hänvisningar"

    def to_dict(self):
        return super().to_dict(include_ordbok=False) | {"Fält": self.field, "Text": markup_cell(self.value)}


too_many = 2


def test_so_too_many_references(entries):
    for entry in tqdm(entries, desc="Finding SO entries with too many references"):
        body = visible_part(entry.entry.get("so", {}))

        for path in json.all_paths(body):
            field = json.path_str(path, strip_positions=True)
            if field.endswith("etymologi"):
                continue
            value = json.get_path(path, body)
            if not isinstance(value, str):
                continue

            reference_count = len(list(ref_regexp.findall(value)))
            if reference_count >= too_many:
                yield SOTooManyReferences(entry, SO, field, value)
