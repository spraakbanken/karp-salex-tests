from karp.foundation import json
from collections import defaultdict, Counter
import re
from utils.salex import EntryWarning, entry_cell, SAOL, SO, parse_böjning, is_visible, variant_forms
from utils.testing import markup_cell
from tqdm import tqdm
from karp.lex.domain.dtos import EntryDto
from dataclasses import dataclass
import utils.markup_parser

@dataclass(frozen=True)
class InflectionWarning(EntryWarning):
    inflection: str
    forms: list[str]

    def category(self):
        return "Böjningsformer"

    def to_dict(self):
        return super().to_dict() | {
            "Böjning": markup_cell(self.inflection),
            "Misstänksamma böjningsformer": ", ".join(self.forms),
        }

#exceptions = "illa litet jag prinsregent envar halvannan skola endera dålig kunna vilkendera petit-chou mycken inner marxism-leninism bakända någondera föga liten mången lite gärna mycket god ond väl gammal bestjäla stjäla".split() 
exceptions = []

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
    "bringa": ["bragd", "bragte", "bragt"],
    "skäla": ["stal", "stulit", "stulen", "stulna", "stulet"],
}

prefix_changes = {
    "ingen": ["inget", "inga"],
    "den": ["det", "de"],
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
    "mar": "mr",
    "ljd": "ld",
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


def check(inflection, entry, namespace, orig_böjning, böjning, word):
    #word = word.lower()
    #simplified = böjning.lower().replace("(", "").replace(")", "").replace(".", ".  ").replace("[", " [")
    #word_suffix = " ".join(word.split()[1:])
    first_word = word.split()[0]
    #simplified = simplified.replace(" " + word_suffix, " ")
    #simplified = re.sub(r"\[[^]]*]", "", simplified)

    if word != first_word: return
    böjning = [x for b in böjning for x in b.split()]

    inflection_tables = [
        f for w in [word, *variant_forms(entry)]
        for f in inflection.inflected_forms(entry, w)]

    böjning = [case for case in böjning if case not in inflection_tables]

    if any(suspicious(first_word, case) for case in böjning):
        yield InflectionWarning(entry, namespace, orig_böjning, [case for case in böjning if suspicious(first_word, case)])




def suspicious(word, case):
    orig_word = word
    # if case in ["el.", "pres.", "n.", "pl."]: return False
    #case = case.replace(",", "")
    #if case in ["i", "och", "vid", "uppräkning", "saknas", "som", "används", "hellre", "än"]:
    #    return False
    #if not case: return False
    #if "." in case:
    #    return False
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
        if word.endswith(suffix) or orig_word.endswith(suffix):
            for replacement in replacements:
                if case.endswith(replacement) and not case.endswith(suffix):
                    case = case[: -len(replacement)] + suffix

    for prefix, replacements in prefix_changes.items():
        if word.startswith(prefix) or orig_word.startswith(prefix):
            for replacement in replacements:
                if case.startswith(replacement) and not case.startswith(prefix):
                    case = prefix + case[len(replacement):]

    prefix = lcp(word, case)
    result = len(prefix) < len(word) - 2
    # if result: print(word, case, vowel_num)
    return result

def test_böjningar(entries, inflection):
    for entry in tqdm(entries, desc="Checking inflected forms"):
        word = entry.entry.get("ortografi")
        if len(word.split()) > 1: continue
        if word in exceptions: continue
        for namespace in [SAOL, SO]:
            if namespace.path not in entry.entry or not is_visible(namespace.path, entry.entry): continue
            orig_böjning = entry.entry.get(namespace.path, {}).get("böjning", "")
            böjning = parse_böjning(entry, namespace)
            yield from check(inflection, entry, namespace, orig_böjning, böjning, word)
