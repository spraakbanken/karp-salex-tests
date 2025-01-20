from karp.foundation import json
from collections import defaultdict, Counter
import pickle
import re

single_changes = {
    "a": ["ä", "ö", "o"],
    "i": ["a", "e", "u", "å"],
    "o": ["ö"],
    "u": ["ö", "y"],
    "y": ["ö", "u"],
    "å": ["ä", "ö"],
    "ä": ["a", "u", "å", "o"],
    "ö": ["u", "o"],
}

suffix_changes = {
    "er": ["rar"],
    "veta": ["visste"],
    "göra": ["gjorde", "gjort"],
    "annan": ["andra"],
    "denna": ["detta", "dessa"],
    "denne": ["detta", "dessa"],
    "säga": ["sagt"],
    "dda": ["tt"],
    "liten": ["små"],
    "vilken": ["vars"],
    "gammal": ["äldre", "äldst"],
    "annan": ["andre", "annat", "andra"],
    "väl": ["bättre", "bäst"],
    "vara": ["är"],
}

unconditional_replacements = {
    "rj": "rd",
    "dj": "dd",
    "gj": "g",
    "gg": "g",
    "skj": "sk",
    "stj": "sk",
    "mm": "m",
    "vart": "var",
}

suffix_drops = ["s"]
vowels = "aeiouyäöå"


def lcp(w1, w2):
    result = []
    changed = False
    while w1 and w2:
        if w1[0] != w2[0] and not changed:
            candidates = single_changes.get(w1[0], [])
            for cand in candidates:
                if w2.startswith(cand):
                    w1 = cand + w1[1:]
                    changed = True
                    break

        if not w1 or not w2 or w1[0] != w2[0]:
            break

        result.append(w1[0])
        w1, w2 = w1[1:], w2[1:]

    return "".join(result)


def check(böjning, word):
    word = word.lower()
    simplified = böjning.lower().replace("(", "").replace(")", "").replace(".", ".  ").replace("[", " [")
    word_suffix = " ".join(word.split()[1:])
    first_word = word.split()[0]
    simplified = simplified.replace(" " + word_suffix, " ")
    simplified = re.sub(r"\[[^]]*]", "", simplified)

    if any(suspicious(first_word, case) for case in simplified.split()):
        print(f"{word}: {böjning} -- {[case for case in simplified.split() if suspicious(first_word, case)]}")


def suspicious(word, case):
    # if case in ["el.", "pres.", "n.", "pl."]: return False
    if "." in case:
        return False
    if not case[0].isalpha():
        return False

    for from_, to in unconditional_replacements.items():
        word = word.replace(from_, to)
        case = case.replace(from_, to)

    for suffix in suffix_drops:
        if word.endswith(suffix) and case.endswith(suffix):
            word = word[: -len(suffix)]
            case = case[: -len(suffix)]

    for suffix, replacements in suffix_changes.items():
        if word.endswith(suffix):
            for replacement in replacements:
                if case.endswith(replacement):
                    case = case[: -len(replacement)] + suffix

    prefix = lcp(word, case)
    result = len(prefix) < len(word) - 2
    # if result: print(word, case, vowel_num)
    return result


entries = list(entry_queries.all_entries("salex", expand_plugins=False))
# with open("entries.pickle", "rb") as file:
#    entries = pickle.load(file)

for entry in entries:
    for saol_lemma in entry.entry.get("SAOLLemman", []):
        word = entry.entry.get("ortografi")
        if not saol_lemma.get("visas"):
            continue
        böjning = saol_lemma.get("böjning")
        if böjning:
            check(böjning, word)

exit()
