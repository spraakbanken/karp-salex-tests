from tqdm import tqdm
from collections import defaultdict
from utils.salex import is_visible, EntryWarning, SO, SAOL, parse_böjning, variant_forms
from dataclasses import dataclass
from copy import deepcopy


@dataclass(frozen=True)
class EntryMissingInSAOL(EntryWarning):
    def collection(self):
        return "Extra"

    def category(self):
        return "SO-ingångar inte i SAOL"

    def to_dict(self):
        return super().to_dict(include_ordbok=False)


def test_saol_missing(entries, inflection):
    # Pair up SO-only and SAOL-only lemmas
    lemmas = {SAOL: defaultdict(list), SO: defaultdict(list)}
    extras = set()

    for entry in tqdm(entries, desc="Finding SO entries not in SAOL"):
        entry = deepcopy(entry)
        for namespace, other_namespace in [(SAOL, SO), (SO, SAOL)]:
            if namespace.path in entry.entry and (is_visible(namespace.path, entry.entry) if namespace == SO else True):
                word_class = entry.entry["ordklass"]
                lemmas[namespace][entry.entry["ortografi"]].append(entry)

        ortografi = entry.entry["ortografi"]
        böjningar = parse_böjning(entry, SAOL)
        variants = variant_forms(entry, SAOL)
        forms = [f for form in [ortografi, *variants] for f in inflection.inflected_forms(entry, form)]
        extras.update(böjningar)
        extras.update(variants)
        extras.update(forms)

    for key, entry_set in lemmas[SO].items():
        if key not in lemmas[SAOL] and key not in extras:
            for entry in entry_set:
                yield EntryMissingInSAOL(entry, SO)
