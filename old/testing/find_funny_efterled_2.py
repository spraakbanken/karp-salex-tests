from karp.foundation import json
from collections import defaultdict, Counter
import pickle
import re


def skeleton(böjning, word):
    word_suffix = " ".join(word.split()[1:])
    böjning = böjning.replace(word_suffix, "")
    simplified = re.sub(r"\[[^]]*]", "", böjning)
    #    print("simplified", simplified)
    return tuple(simplified.split())


def absolute(böjning, word):
    return [w for w in skeleton(böjning, word) if w[0].isalpha()]


böjningar = defaultdict(set)

entries = list(entry_queries.all_entries("salex", expand_plugins=False))
##with open("entries.pickle", "rb") as file:
#    entries = pickle.load(file)

for entry in entries:
    if saol_lemma := entry.entry.get("saol"):
        word = entry.entry.get("ortografi")
        if not saol_lemma.get("visas"):
            continue
        böjning = saol_lemma.get("böjning")
        if not böjning:
            continue

        for form in absolute(böjning, word):
            böjningar[form].add(word)

for form, words in böjningar.items():
    suffixes = {}
    for w in words:
        for w2 in words:
            if w.endswith(w2) and w != w2:
                suffixes[w] = w2

    if suffixes:
        print(f'{", ".join(suffixes)}: "{form}"')

exit()
