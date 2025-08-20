from tqdm import tqdm
from collections import Counter, defaultdict
from utils.salex import is_visible, EntryWarning, SAOL, parse_böjning, entry_sort_key, entry_cell
from utils.testing import markup_cell
from dataclasses import dataclass
import re
from collections import defaultdict
from bisect import bisect_left

@dataclass(frozen=True)
class SegmentationWarning(EntryWarning):
    ordled: str
    neighbours: list[object]
    neighbours_backwards: list[object]

    def category(self):
        return f"Segmentering ({self.namespace})"

    def to_dict(self):
        return super().to_dict(include_ordbok=False) | {
            "Ordled": self.ordled,
            "Grannar": ", ".join(entry_ordled(e) for e in self.neighbours),
            "Grannar (baklänges)": ", ".join(entry_ordled(e) for e in self.neighbours_backwards),
        }

dot = "·"
bar = "|"
separators = re.compile(fr"[{dot}{bar}]")

def word_morphemes(word):
    return word.split(bar)

def word_segments(word):
    return separators.split(word)

def entry_ordled(entry):
    return entry.entry["saol"].get("ordled", entry.entry["ortografi"])

def neighbours(item, arr, size=3, key=None):
    if key is None: key = lambda x: x
    pos = bisect_left(arr, key(item), key=key)
    if pos != len(arr) and arr[pos] == item:
        for i in range(pos-size, pos+size+1):
            if i >= 0 and i < len(arr):
                yield arr[i]

def test_word_segmentation(entries):
    by_morpheme = defaultdict(list)
    by_segment = defaultdict(list)
    by_first_morpheme = defaultdict(list)
    by_last_morpheme = defaultdict(list)
    by_first_segment = defaultdict(list)
    by_last_segment = defaultdict(list)
    by_word = defaultdict(list)

    for entry in tqdm(entries, desc="Building word segmentation indexes"):
        if not entry.entry.get("saol"): continue
        by_word[entry.entry["ortografi"]].append(entry)

        ordled = entry_ordled(entry)

        morphemes = word_morphemes(ordled)
        segments = word_segments(ordled)

        for m in morphemes: by_morpheme[m].append(entry)
        for s in segments: by_segment[s].append(entry)
        by_first_morpheme[morphemes[0]].append(entry)
        by_last_morpheme[morphemes[-1]].append(entry)
        by_first_segment[segments[0]].append(entry)
        by_last_segment[segments[-1]].append(entry)

    all_words = list(sorted(by_word))
    all_words_rev = list(sorted(by_word, key = lambda s: s[::-1]))

    def neighbouring_words(word, size=1, prefix=True, suffix=True):
        if prefix:
            yield from neighbours(word, all_words, size=size)
        if suffix:
            yield from neighbours(word, all_words_rev, size=size, key=lambda s: s[::-1])

    def neighbouring_entries(entry, size=3, prefix=True, suffix=True):
        word = entry.entry["ortografi"]
        for w in neighbouring_words(word, size, prefix, suffix):
            for e in by_word[w]:
                if e == entry: continue
                yield e
    
    for entry in tqdm(entries, desc="Checking word segmentation"):
        if not entry.entry.get("saol"): continue
        ordled = entry_ordled(entry)

        morphemes = word_morphemes(ordled)
        segments = word_segments(ordled)

        if len(morphemes) == 1: continue

        neighbours_forwards = list(neighbouring_entries(entry, prefix=True, suffix=False))
        neighbours_backwards = list(neighbouring_entries(entry, prefix=False, suffix=True))

        if len(by_first_morpheme[morphemes[0]]) == 1 and len(by_last_morpheme[morphemes[-1]]) == 1:
            yield SegmentationWarning(entry, SAOL, ordled, neighbours_forwards, neighbours_backwards)
