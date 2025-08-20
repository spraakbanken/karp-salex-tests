from tqdm import tqdm
from collections import Counter, defaultdict
from utils.salex import is_visible, EntryWarning, SAOL, parse_böjning, entry_sort_key, entry_cell, visible_part
from utils.testing import markup_cell
from dataclasses import dataclass
import re
from collections import defaultdict, Counter
from bisect import bisect_left
from itertools import islice
from karp.foundation import json

@dataclass(frozen=True)
class SegmentationWarning(EntryWarning):
    ordled: str
    neighbours: list[object]
    neighbours_backwards: list[object]
    info: str

    def category(self):
        return f"Segmentering ({self.namespace})"

    def to_dict(self):
        return super().to_dict(include_ordbok=False) | {
            "Ordled": self.ordled,
            "Grannar": ", ".join(entry_ordled(e) for e in self.neighbours),
            "Grannar (baklänges)": ", ".join(entry_ordled(e) for e in self.neighbours_backwards),
            "Info": self.info,
        }

@dataclass(frozen=True)
class SegmentationWarning2(EntryWarning):
    ordled: str
    plain_morpheme: str
    notated_morpheme: str
    common_morpheme: str
    common_morpheme_words: list[object]

    def collection(self):
        return "Ordledstestning"

    def category(self):
        if "·" not in self.notated_morpheme or "·" not in self.common_morpheme:
            return f'Punkt saknas helt'
        elif is_subsequence(self.notated_morpheme, self.common_morpheme) or is_subsequence(self.common_morpheme, self.notated_morpheme):
            return f'Minst en punkt saknas'
        else:
            return f'Avvikande punkter'

    def to_dict(self):
        return super().to_dict(include_ordbok=False) | {
            "Ordled": self.ordled,
#            "Morfem": self.notated_morpheme,
            "Vanligare form": f"{self.common_morpheme} ({len(self.common_morpheme_words)} förekomst{'er' if len(self.common_morpheme_words)>1 else ''})",
            "Exempel med vanligare form": entry_cell(self.common_morpheme_words[0], self.namespace),
        }

    def sort_key(self):
        return (self.plain_morpheme, self.notated_morpheme, entry_sort_key(self.entry, self.namespace))

word_separators = re.compile(r"[ \-]")
morpheme_separators = re.compile(r"[ \-|]")
segment_separators = re.compile(r"[ \-·|]")

def words(word):
    return word_separators.split(word)

def word_morphemes(word):
    return morpheme_separators.split(word)

def word_segments(word):
    return segment_separators.split(word)

def entry_ordled(entry):
    return entry.entry["saol"].get("ordled", entry.entry["ortografi"])

class SortedSet:
    def __init__(self, items, key=None):
        if key is None: key=lambda x: x
        self.items = list(sorted(items, key=key))
        self.key = key

    def neighbours(self, item, size=3):
        pos = bisect_left(self.items, self.key(item), key=self.key)
        if pos != len(self.items) and self.items[pos] == item:
            for i in range(pos-size, pos+size+1):
                if i >= 0 and i < len(self.items):
                    yield self.items[i]

    def following(self, item):
        pos = bisect_left(self.items, self.key(item), key=self.key)
        if pos != len(self.items) and self.items[pos] == item:
            for i in range(pos+1, len(self.items)):
                yield self.items[i]

    def preceding(self, item):
        pos = bisect_left(self.items, self.key(item), key=self.key)
        if pos != len(self.items) and self.items[pos] == item:
            for i in range(pos-1, -1, -1):
                yield self.items[i]

#def base_morphemes(morpheme):
#    if morpheme.endswith("s") and not morpheme.endswith("ss"): morpheme = morpheme[:-1]
#    yield morpheme
#    #if morpheme.endswith("s"): yield morpheme[:-1]

def is_subsequence(s1, s2):
    i = 0
    j = 0
    while i < len(s1) and j < len(s2):
        if s1[i] == s2[j]:
            i += 1
            j += 1
        else:
            j += 1
    return i == len(s1)

def strip_markup(word):
    return "".join(word_segments(word))

def test_word_segmentation(entries):
    by_morpheme = defaultdict(list)
    decorated_morphemes = defaultdict(lambda: defaultdict(list))
    by_segment = defaultdict(list)
    by_first_morpheme = defaultdict(list)
    by_last_morpheme = defaultdict(list)
    by_first_segment = defaultdict(list)
    by_last_segment = defaultdict(list)
    by_word = defaultdict(list)

    saol_entries = []

    for entry in tqdm(entries, desc="Reading SAOL entries"):
        body = visible_part(entry.entry)
        if "saol" not in body: continue
        saol_entries.append(entry)

    for entry in tqdm(saol_entries, desc="Building segmentation indexes"):
        by_word[entry.entry["ortografi"]].append(entry)
        ordled = entry_ordled(entry)

        morphemes = word_morphemes(ordled)
        segments = word_segments(ordled)

        for m in morphemes: by_morpheme[m].append(entry)
        for i, m in enumerate(morphemes):
            if i == 0 and len(morphemes) > 1 and m.endswith("s") and not m.endswith("ss"):
                m = m[:-1]
                # e.g. sinn·es => sinn·e which we change to sinne
                if len(m) > 2 and m[-2] == "·":
                    m = m[:-2] + m[-1]
            decorated_morphemes[strip_markup(m)][m].append(entry)
        for s in segments: by_segment[s].append(entry)
        by_first_morpheme[morphemes[0]].append(entry)
        by_last_morpheme[morphemes[-1]].append(entry)
        by_first_segment[segments[0]].append(entry)
        by_last_segment[segments[-1]].append(entry)

#    breakpoint()

    for plain, ms in decorated_morphemes.items():
        counts = Counter({m: len(es) for m, es in ms.items()})
        correct, _ = counts.most_common(1)[0]

        for m, es in ms.items():
            if m == correct: continue
            for e in es:
                yield SegmentationWarning2(e, SAOL, entry_ordled(e), plain, m, correct, ms[correct])

    return

    sorted_entries = SortedSet(saol_entries, key=lambda e: e.entry["ortografi"])
    rev_sorted_entries = SortedSet(saol_entries, key=lambda e: e.entry["ortografi"][::-1])

    for entry in tqdm(saol_entries, desc="Checking word segmentation"):
        ordled = entry_ordled(entry)
        neighbours_forwards = list(sorted_entries.neighbours(entry))
        neighbours_backwards = list(rev_sorted_entries.neighbours(entry))

        for word in words(ordled):
            morphemes = word_morphemes(word)
            segments = word_segments(word)

            if len(morphemes) > 1 and len(by_first_morpheme[morphemes[0]]) == 1 and len(by_last_morpheme[morphemes[-1]]) == 1:
                yield SegmentationWarning(entry, SAOL, ordled, neighbours_forwards, neighbours_backwards, "morphemes")

            elif len(segments) > 1 and len(by_first_segment[segments[0]]) == 1 and len(by_last_segment[segments[-1]]) == 1:
                yield SegmentationWarning(entry, SAOL, ordled, neighbours_forwards, neighbours_backwards, "segments")

            if len(morphemes) > 1:
                for m in morphemes:
                    if len(decorated_morphemes[m]) > 1 and len(by_morpheme[m]) == 1:
                        yield SegmentationWarning(entry, SAOL, ordled, [], [], "decorated " + ", ".join(decorated_morphemes[m]))


