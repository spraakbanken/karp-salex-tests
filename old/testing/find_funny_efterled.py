from karp.foundation import json
from collections import defaultdict, Counter
import pickle
import re
import tqdm


def absolute(böjning, word):
    word_suffix = " ".join(word.split()[1:])
    böjning = böjning.replace(word_suffix, "")
    simplified = re.sub(r"\[[^]]*]", "", böjning)
    #    print("simplified", simplified)
    return any(w[0].isalpha() for w in simplified.split())


böjningar = defaultdict(set)

entries = list(entry_queries.all_entries("salex", expand_plugins=False))
# with open("entries.pickle", "rb") as file:
#    entries = pickle.load(file)

for entry in tqdm.tqdm(entries):
    if saol_lemma := entry.entry.get("saol"):
        word = entry.entry.get("ortografi")
        if not saol_lemma.get("visas"):
            continue
        böjning = saol_lemma.get("böjning")
        if not böjning or not absolute(böjning, word):
            continue

        böjningar[böjning].add(word)

for böjning, words in böjningar.items():
    if len(words) > 1:
        print(f'{böjning}: {", ".join(words)}')

exit()
