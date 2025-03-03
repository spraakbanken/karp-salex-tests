from karp.foundation import json
from nltk.tokenize import word_tokenize
from enum import global_enum, Enum
import re
from utils.salex import is_visible, EntryWarning, SAOL, SO, parse_böjning, variant_forms
from utils.testing import highlight
from utils.markup_parser import strip_markup
from tqdm import tqdm
from dataclasses import dataclass


@dataclass(frozen=True)
class MissingOrForbiddenWord(EntryWarning):
    field: str
    text: str
    missing: list[str] | None
    forbidden: list[str] | None

    def category(self):
        descr = "korta" if len(self.entry.entry["ortografi"]) <= 3 else "långa"
        return f"Språkprov osv ({self.namespace}) {descr}"

    def to_dict(self):
        text = self.text
        if self.forbidden: text = highlight(self.forbidden, text, case_sensitive=False)
        return super().to_dict() | {
            "Mening": text,
        }


@global_enum
class Kind(Enum):
    ABBREV = 0
    UNABBREV = 1


fields = {
    "so.huvudbetydelser.idiom.idiombetydelser.exempel": (SO, UNABBREV),
    "so.huvudbetydelser.syntex.text": (SO, UNABBREV),
    "so.huvudbetydelser.underbetydelser.syntex.text": (SO, UNABBREV),
    "saol.huvudbetydelser.exempel.text": (SAOL, ABBREV),
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


def check_text(entry, namespace, field, ortografi, böjningar, text, kind):
    orig_text = text

    # If not a proper noun, match should be case-insensitive
    if not ortografi.isupper():
        ortografi = ortografi.lower()
        text = text.lower()
        böjningar = [b.lower() for b in böjningar]

    # Don't abbreviate if word is <= 2 letters
    #if len(ortografi) <= 2 and kind == ABBREV:
    #    kind = UNABBREV
    
    def is_abbrev(w):
        return len(w) == 2 and w[0].isalpha() and w[1] == "."

    if kind == ABBREV:
        # TODO forbid ortografi
        forbidden = [c + "." for c in letters if c != ortografi[0]] + [ortografi]
        compulsory = [ortografi[0] + "."] + [ortografi] + böjningar
    else:
        #forbidden = [c + "." for c in letters]
        forbidden = [ortografi[0] + "."]
        compulsory = [ortografi] + böjningar

    tokens = tokenize(text)

    problem_missing = []
    problem_forbidden = []

    for f in forbidden:
        ts = tokenize(f)
        if contains_sublist(ts, tokens, startswith=False):
            problem_forbidden.append(f)

    for c in compulsory:
        ts = tokenize(c)
        if contains_sublist(ts, tokens, startswith=True):
            break
    else:
        problem_missing += compulsory

    if problem_missing or problem_forbidden:
        yield MissingOrForbiddenWord(entry, namespace, field, orig_text, missing=problem_missing, forbidden=problem_forbidden)

def test_examples(entries, inflection):
    for entry in tqdm(entries, desc="Checking example sentences"):
        for field, (namespace, kind) in fields.items():
            böjningar1 = parse_böjning(entry, SO)  # decode_böjning(entry.entry.get("so", {}).get("böjning", ""))
            böjningar2 = parse_böjning(
                entry, SAOL
            )  # decode_saol_böjning(entry.entry.get("saol", {}).get("böjning", ""))
            ortografi = entry.entry.get("ortografi")
            if not ortografi:
                continue

            inflectiontables = [
                f for v in [ortografi, *variant_forms(entry)] for f in inflection.inflected_forms(entry, v)
            ]
            if ortografi.startswith("-") or ortografi.endswith("-") or len(ortografi.split()) > 1:  # not supported yet
                continue

            for path in json.expand_path(field, entry.entry):
                if not is_visible(path, entry.entry):
                    continue
                value = strip_markup(json.get_path(path, entry.entry))

                yield from check_text(
                    entry, namespace, field, ortografi, böjningar1 + böjningar2 + inflectiontables, value, kind
                )
