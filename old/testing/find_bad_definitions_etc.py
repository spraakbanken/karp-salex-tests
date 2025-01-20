from karp.foundation import json
from collections import defaultdict, Counter
from nltk.tokenize import word_tokenize
from enum import global_enum, Enum
import re
import sys

sys.path.append("/home/nick/prog/sb/karp-backend/repl_scripts/testing")
from testing_utils import *


@global_enum
class Kind(Enum):
    ABBREV = 0
    UNABBREV = 1


fields = {
    #    "so.huvudbetydelser.idiom.idiombetydelser.exempel": UNABBREV,
    #    "so.huvudbetydelser.syntex.text": UNABBREV,
    #    "so.huvudbetydelser.underbetydelser.syntex.text": UNABBREV,
    "saol.huvudbetydelser.exempel.text": ABBREV
}


def decode_böjning(böjning):
    return [match.groups()[0] for match in re.finditer(r"\[i ([^]]*)]", böjning)]


def decode_saol_böjning(böjning):
    result = []
    while True:
        if (pos := böjning.find("[")) == -1:
            result.append(böjning)
            break

        result.append(böjning[:pos])
        if (pos2 := böjning[pos:].find("]")) == -1:
            break
        else:
            böjning = böjning[pos2 + 1 :]

    return result


def alternatives(w):
    yield w


def tokenize(text):
    result = []
    tokens = word_tokenize(text, language="swedish")
    while tokens:
        # combine e.g. ['m', '.'] into one token
        if len(tokens) >= 2 and len(tokens[0]) == 1 and tokens[0].isalpha() and tokens[1] == ".":
            result.append(tokens[0] + tokens[1])
            tokens = tokens[2:]
        else:
            result.append(tokens[0])
            tokens = tokens[1:]
    return result


letters = "abcdefghijklmnopqrstuvwxyzåäö"


def contains_sublist(needle, haystack, startswith=False):
    for i in range(len(haystack)):
        compare = haystack[i : i + len(needle)]

        if startswith:
            if all(any(c.startswith(n1) or c.endswith(n1) for n1 in alternatives(n)) for n, c in zip(needle, compare)):
                return True
        else:
            if all(c in alternatives(n) for n, c in zip(needle, compare)):
                return True

    return False


def check_text(ortografi, böjningar, text, kind):
    # If not a proper noun, match should be case-insensitive
    if not ortografi[0].isupper():
        ortografi = ortografi.lower()
        text = text.lower()

    def is_abbrev(w):
        return len(w) == 2 and w[0].isalpha() and w[1] == "."

    if kind == ABBREV:
        # TODO forbid ortografi
        forbidden = [c + "." for c in letters if c != ortografi[0]]
        compulsory = [ortografi[0] + "."] + [ortografi] + böjningar
    else:
        forbidden = [c + "." for c in letters]
        compulsory = [ortografi] + böjningar

    tokens = tokenize(text)

    for f in forbidden:
        ts = tokenize(f)
        if contains_sublist(ts, tokens, startswith=False):
            print("forbidden", ortografi, f)
            print(text)
            print()

    for c in compulsory:
        ts = tokenize(c)
        if contains_sublist(ts, tokens, startswith=True):
            break
    else:
        print("missing", ortografi, compulsory)
        print(text)
        print()


entries = entry_queries.all_entries("salex", expand_plugins=True)

for field, kind in fields.items():
    print("===>", field)
    for entry in entries:
        böjningar1 = decode_böjning(entry.entry.get("so", {}).get("böjning", ""))
        böjningar2 = decode_saol_böjning(entry.entry.get("saol", {}).get("böjning", ""))
        inflectiontables = [
            json.get_path(path, entry.entry)
            for field in [
                "saol._inflectiontable.rows.fields.preform.form",
                "saol.alt._inflectiontable.rows.fields.preform.form",
            ]
            for path in json.expand_path(field, entry.entry)
        ]
        # print(inflectiontables)
        ortografi = entry.entry.get("ortografi")
        if not ortografi:
            continue

        for path in json.expand_path(field, entry.entry):
            if not is_visible(path, entry):
                continue
            value = json.get_path(path, entry.entry)
            check_text(ortografi, böjningar1 + böjningar2 + inflectiontables, value, kind)

    print()

exit()
