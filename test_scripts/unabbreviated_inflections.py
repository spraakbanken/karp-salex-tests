from tqdm import tqdm
from collections import Counter, defaultdict
from utils.salex import is_visible, EntryWarning, SAOL, parse_böjning, entry_sort_key, entry_cell, SO
from utils.testing import markup_cell
from dataclasses import dataclass
import re

@dataclass(frozen=True)
class UnabbreviatedInflection(EntryWarning):
    inflection: str | None
    error: str

    def category(self):
        return f"{self.error} ({self.namespace})"

    def to_dict(self):
        return super().to_dict(include_ordbok=False) | {
            "Böjning": markup_cell(self.inflection or ""),
        }

def abbreviations_ok(entry, namespace):
    ortografi = entry.entry["ortografi"]
    forms = parse_böjning(entry, namespace, only_alpha=False)

    for form in forms:
        for f in form.split():
            if "~:" in form: yield "Tilde-kolon"
            if entry.entry.get("saol", {}).get("variantformer"): continue
            if f.startswith(ortografi):
                if f.startswith(ortografi + ":"): yield "Tilde saknas (kolon)"
                elif f == ortografi: yield "Tilde saknas (helt ord)"
                else: yield "Tilde saknas"


def test_unabbreviated_inflections(entries):
    for entry in tqdm(entries, desc="Checking inflection abbreviations"):
        for namespace in [SAOL]:
            errors = set(abbreviations_ok(entry, namespace))
            if "Tilde saknas" in errors:
                if "Tilde saknas (kolon)" in errors: errors.remove("Tilde saknas (kolon)")
                if "Tilde saknas (helt ord)" in errors: errors.remove("Tilde saknas (helt ord)")
            for err in errors:
                yield UnabbreviatedInflection(entry, namespace, entry.entry[namespace.path]["böjning"], err)
