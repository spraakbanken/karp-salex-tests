from utils.salex import visible_part, full_ref_regexp, EntryWarning, SO, entry_cell
from tqdm import tqdm
from karp.foundation import json
from karp.lex.domain.dtos import EntryDto
from nltk.tokenize import RegexpTokenizer
from collections import Counter, defaultdict
from test_scripts.references import refid_re

from dataclasses import dataclass


@dataclass(frozen=True)
class EndingLinkSuggestion(EntryWarning):
    pattern: tuple[str, str]
    frequency: int
    definition: str
    suggestion: EntryDto

    def collection(self):
        return f"Definitioner {self.namespace}"

    def category(self):
        return f"Definitioner relaterade {self.namespace}"

    def to_dict(self):
        return super().to_dict(include_ordbok=False) | {
            "Definition": self.definition,
            "Mönster": f"-{self.pattern[0]} => -{self.pattern[1]}",
            "HV": entry_cell(self.suggestion, SO),
        }

    def sort_key(self):
        return (self.pattern, super().sort_key())


definition_fields = {"so.huvudbetydelser.definition", "so.huvudbetydelser.underbetydelser.definition"}

tokenizer = RegexpTokenizer(r"\w+")


def unref(s):
    return full_ref_regexp.subn("REF", s)[0]


def tokenize(s):
    return tuple(tokenizer.tokenize(unref(s)))


common_letters = 5


def common_prefix(w1, w2):
    return len(w1) >= common_letters and len(w2) >= common_letters and w1[:common_letters] == w2[:common_letters]


def strip_prefix(w1, w2):
    while w1 and w2 and w1[0] == w2[0]:
        w1 = w1[1:]
        w2 = w2[1:]

    return w1, w2


def test_so_endings(entries):
    words = defaultdict(list)
    for entry in tqdm(entries, desc="Collecting words"):
        if "so" in entry.entry and entry.entry["so"].get("visas", True):
            words[entry.entry["ortografi"]].append(entry)

    rules = Counter()
    not_rules = Counter()
    not_rules_entries = defaultdict(list)
    totals = Counter()

    for i, entry in tqdm(enumerate(entries), desc="Finding similar words"):
        body = visible_part(entry.entry)
        word = body["ortografi"]
        for definition_field in definition_fields:
            for definition_path in json.expand_path(definition_field, body):
                definition = json.get_path(definition_path, body)
                for def_word in tokenize(definition):
                    if word != def_word and common_prefix(word, def_word):
                        a, b = strip_prefix(word, def_word)
                        totals[a, b] += 1
                        not_rules[a, b] += 1
                        not_rules_entries[a, b].append((entry, def_word, definition))

                for link in refid_re.finditer(definition):
                    def_word = link.group(1).replace("_", " ")
                    if word != def_word and common_prefix(word, def_word):
                        a, b = strip_prefix(word, def_word)
                        totals[a, b] += 1
                        rules[a, b] += 1

    for (a, b), total_count in totals.most_common():
        count = rules[a, b]
        not_count = not_rules[(a, b)]
        if count <= 1 or not_count == 0:
            continue
        for entry, word, definition in not_rules_entries[a, b]:
            if len(words[word]) >= 1:
                suggestion = words[word][0]
                hb = visible_part(suggestion.entry)["so"]["huvudbetydelser"]
                if len(hb) == 1 or True:
                    yield EndingLinkSuggestion(entry, SO, (a, b), not_count, definition, suggestion)
