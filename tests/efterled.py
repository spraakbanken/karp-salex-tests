from karp.foundation import json
from collections import defaultdict, Counter
import re
from utils.salex import EntryWarning, entry_cell, SAOL
from tqdm import tqdm
from karp.lex.domain.dtos import EntryDto
from dataclasses import dataclass

@dataclass(frozen=True)
class InflectionWarning(EntryWarning):
    inflection: str
    form: str
    parent: EntryDto

    def category(self):
        return "Misstänksamma böjningsformer"

    def to_dict(self):
        return super().to_dict() | {
            "Böjningsform": self.form,
            "Kopierad från?": entry_cell(self.parent, self.namespace),
            "Böjning": self.inflection
        }

def skeleton(böjning, word):
    word_suffix = " ".join(word.split()[1:])
    böjning = böjning.replace(word_suffix, "")
    simplified = re.sub(r"\[[^]]*]", "", böjning)
    #    print("simplified", simplified)
    return tuple(simplified.split())


def absolute(böjning, word):
    return [w for w in skeleton(böjning, word) if w[0].isalpha()]


def test_efterled(entries_by_id):
    böjningar = defaultdict(list)

    for entry in tqdm(entries_by_id.values(), desc="Checking inflected forms for suffixes"):
        if saol_lemma := entry.entry.get("saol"):
            word = entry.entry["ortografi"]
            if not saol_lemma.get("visas"):
                continue
            böjning = saol_lemma.get("böjning")
            if not böjning:
                continue

            for form in absolute(böjning, word):
                böjningar[form].append(entry)

    for form, entries in böjningar.items():
        suffixes = {}
        for e in entries:
            w = e.entry["ortografi"]
            for e2 in entries:
                w2 = e2.entry["ortografi"]
                if w.endswith(w2) and w != w2:
                    suffixes[e.id] = e2

        for entry_id, suffix in suffixes.items():
            entry = entries_by_id[entry_id]
            yield InflectionWarning(entry, SAOL, entry.entry["saol"]["böjning"], form, suffix)
