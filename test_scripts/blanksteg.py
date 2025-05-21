from utils.salex import SAOL, SO, FieldWarning, is_visible
from dataclasses import dataclass
from tqdm import tqdm
from karp.foundation import json


@dataclass(frozen=True)
class Blanksteg(FieldWarning):
    def collection(self):
        return "Extra"

    def category(self):
        return "Extra blanksteg"

    def to_dict(self):
        return super().to_dict()


def test_blanksteg(entries):
    for entry in tqdm(entries, desc="Checking spaces"):
        for path in json.all_paths(entry.entry):
            if not is_visible(path, entry.entry):
                continue
            value = json.get_path(path, entry.entry)
            if not isinstance(value, str):
                continue

            if path[0] == "so":
                namespace = SO
                path = path[1:]
            elif path[0] == "saol":
                namespace = SAOL
                path = path[1:]
            else:
                namespace = None

            if value.strip().replace("  ", " ") != value.removesuffix("\n"):
                yield Blanksteg(entry, namespace, path, None)
