from karp.foundation import json
from collections import Counter, defaultdict
from nltk.tokenize import RegexpTokenizer
from tqdm import tqdm
from utils.salex import visible_part, full_ref_regexp, variant_forms, SO, EntryWarning, entry_cell, entry_sort_key, parse_böjning
from karp.lex.domain.dtos import EntryDto
from enum import Enum, global_enum
from copy import deepcopy
from dataclasses import dataclass

@dataclass(frozen=True)
class DefinitionLinkSuggestion(EntryWarning):
    pattern: str
    definition: str
    suggestions: list[EntryDto]

    def collection(self):
        return f"Definitioner {self.namespace}"

    def category(self):
        return f"Definitioner {self.namespace}"

    def to_dict(self):
        result = super().to_dict(include_ordbok=False) | {
            "Definition": self.definition
        }

        for i, entry in enumerate(self.suggestions, start=1):
            result[f"HV {i}"] = entry_cell(entry, self.namespace)

        return result

    def sort_key(self):
        return (self.pattern, super().sort_key())

@global_enum
class Kind(Enum):
    LEMMA = 0
    VARIANT = 1
    VNOMEN = 2
    BÖJNINGSFORM = 3

def similar(d1, d2, n=1):
    if len(d1) != len(d2): return False

    for w1, w2 in zip(d1, d2):
        if w1 == w2: continue
        elif w1 == "REF" and not w2[0].isupper() and n > 0:
            n -= 1
        else:
            return False
    
    return True

def match(d1, d2):
    for w1, w2 in zip(d1, d2):
        if w1 == "REF":
            return w2

    raise AssertionError("didn't match")

fields = ["so.huvudbetydelser.definition",
          #"so.huvudbetydelser.definitionstillägg",
          "so.huvudbetydelser.underbetydelser.definition",
          #"so.huvudbetydelser.underbetydelser.definitionstillägg",
          #"so.huvudbetydelser.idiom.idiombetydelser.definition",
          #"so.huvudbetydelser.idiom.idiombetydelser.definitionstillägg"
          ]

tokenizer = RegexpTokenizer(r'\w+')

def unref(s):
    return full_ref_regexp.subn("REF", s)[0]

def tokenize(s):
    return tuple(tokenizer.tokenize(unref(s)))

def ngram_counts(n, prefix):
    return Counter(d[:n] for d in definitions if d[:len(prefix)] == prefix)

def summarise(n=1, prefix=(), limit=100, indent=0):
    counts = ngram_counts(n, prefix)

    for ngram, count in counts.most_common():
        if ngram == prefix: break

        print(f'{indent * " "}{count} {" ".join(ngram)}')
        if count < limit: break
        summarise(n+1, ngram, limit, indent+2)

#summarise(limit=20)

def test_so_definitions(entries, inflection):
    forms = defaultdict(lambda: defaultdict(list))
    for entry in tqdm(entries, desc="Collecting inflected forms"):
        if "so" in entry.entry and entry.entry["so"].get("visas", True):
            forms[entry.entry["ortografi"]][LEMMA].append(entry)
        variants_plus_vnomen = list(variant_forms(entry, SO))
        if "so" in entry.entry and "vnomen" in entry.entry["so"]:
            entry_no_vnomen = deepcopy(entry)
            del entry.entry["so"]["vnomen"]
            variants = list(variant_forms(entry, SO))
            vnomen = list(set(variants_plus_vnomen) - set(variants))
        else:
            variants = variants_plus_vnomen
            vnomen = []

        for variant in variants:
            forms[variant][VARIANT].append(entry)
        for variant in vnomen:
            forms[variant][VNOMEN].append(entry)
        for variant in variant_forms(entry, SO, include_main_form=True):
            for inflected in set(list(inflection.inflected_forms(entry, variant)) + parse_böjning(entry, SO)):
                if inflected != variant:
                    forms[inflected][BÖJNINGSFORM].append(entry)

    original_definitions = {}

    definitions = defaultdict(list)
    for entry in tqdm(entries, desc="Checking SO definitions"):
        body = visible_part(entry.entry)
        for field in fields:
            for path in json.expand_path(field, body):
                definition = tokenize(json.get_path(path, body))
                definitions[definition].append(entry)
                original_definitions[(definition, entry.id)] = json.get_path(path, body)

    counts = Counter({d: len(es) for d, es in definitions.items()})

    for d, c in counts.items():
        if len([x for x in d if x == "REF"]) == 1 and c >= 10:
            orig = original_definitions[(d, definitions[d][0].id)]
            #print(c, unref(orig))
            for d1, c1 in counts.items():
                if d == d1: continue
                if similar(d, d1):
                    ref_word = match(d, d1)
                    orig = original_definitions[(d1, definitions[d1][0].id)]

                    suggestions = []
                    suggestions += forms[ref_word][LEMMA]
                    suggestions += forms[ref_word][VARIANT]

                    if not suggestions:
                        suggestions += forms[ref_word][VNOMEN]
                        suggestions += forms[ref_word][BÖJNINGSFORM]

                    # remove duplicates
                    suggestions = [x for x in {s.id: s for s in suggestions}.values()]

                    suggestions.sort(key=lambda x: entry_sort_key(x, SO))

                    yield DefinitionLinkSuggestion(definitions[d1][0], SO, d, orig, suggestions)
                    #print("  ", format(definitions[d1][0]) + ":", orig)
                    #for kind, es in forms[ref_word].items():
                    #    for e in es:
                    #        print("     =>", kind, format(e))
