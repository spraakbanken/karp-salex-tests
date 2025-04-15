from tqdm import tqdm
from collections import Counter, defaultdict
from utils.salex import is_visible, EntryWarning, SAOL, parse_böjning, entry_name, entry_sort_key
from utils.testing import markup_cell
from dataclasses import dataclass
import re

uttal_re = re.compile(r" \[r \\\[[^\]]*\\\]\]")


@dataclass(frozen=True)
class SuspiciousInflection(EntryWarning):
    inflection: str | None
    expected_inflection: str | None
    inflection_class: str

    def category(self):
        return f"Böjningar extra test ({self.namespace})"

    def to_dict(self):
        return super().to_dict(include_ordbok=False) | {
            "Böjningsklass": self.inflection_class,
            "Böjning": markup_cell(self.inflection or ""),
            "Vanligast böjning i klassen": markup_cell(self.expected_inflection or ""),
        }

    def sort_key(self):
        return (self.inflection_class, entry_sort_key(self.entry, self.namespace))


def test_inflection_class_vs_inflection(entries):
    by_inflection_class = defaultdict(list)
    for entry in tqdm(entries, desc="Checking inflection classes for consistency"):
        inflection_class = entry.entry.get("böjningsklass")
        if inflection_class is not None:
            by_inflection_class[inflection_class].append(entry)

    for inflection_class, entries in by_inflection_class.items():
        for namespace in [SAOL]:
            inflection_counts = Counter()
            for entry in entries:
                if namespace.path not in entry.entry:
                    continue
                if not is_visible(namespace.path, entry.entry):
                    continue
                if entry.entry.get("ingångstyp") in ["se under", "variant", "reflexivt_verb", "partikelverb"]:
                    continue

                inflection = entry.entry[namespace.path].get("böjning")
                inflection_counts[inflection] += 1

            if inflection_counts:
                expected_inflection, _ = inflection_counts.most_common(1)[0]
                sample_entry = next(
                    e for e in entries if e.entry.get(namespace.path, {}).get("böjning") == expected_inflection
                )

                forms = parse_böjning(sample_entry, namespace, only_alpha=False)
                if not all(f.startswith("~") for form in forms for f in form.split()):
                    continue

            else:
                expected_inflection = None

            if expected_inflection is None:
                continue
            simplified_expected_inflection = uttal_re.sub("", expected_inflection)

            for entry in entries:
                if namespace.path not in entry.entry:
                    continue
                if not is_visible(namespace.path, entry.entry):
                    continue
                if entry.entry.get("ingångstyp") in ["se under", "variant", "reflexivt_verb", "partikelverb"]:
                    continue

                inflection = entry.entry[namespace.path].get("böjning")
                if inflection is None:
                    simplified_inflection = None
                else:
                    simplified_inflection = uttal_re.sub("", inflection)
                if simplified_inflection != simplified_expected_inflection:
                    yield SuspiciousInflection(entry, namespace, inflection, expected_inflection, inflection_class)
