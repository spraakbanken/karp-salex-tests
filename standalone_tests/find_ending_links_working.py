from utils.salex import visible_part, full_ref_regexp
from tqdm import tqdm
from karp.foundation import json
from nltk.tokenize import RegexpTokenizer
import re
from collections import Counter, defaultdict
from test_scripts.references import refid_re

definition_fields = {
    "so.huvudbetydelser.definition",
    "so.huvudbetydelser.underbetydelser.definition"
}

tokenizer = RegexpTokenizer(r'\w+')

def unref(s):
    return full_ref_regexp.subn("REF", s)[0]

def tokenize(s):
    return tuple(tokenizer.tokenize(unref(s)))

entries = []
for entry in tqdm(list(entry_queries.all_entries("salex", expand_plugins=False)), desc="Reading entries"):
    #if entry.entry.get("so", {}) == {}: continue
    entry.entry = visible_part(entry.entry)
    if "so" in entry.entry:
        entries.append(entry)

entries.sort(key=lambda x: x.entry["ortografi"])
interval = 10
common_letters = 5

rules = Counter()
rules_examples = defaultdict(list)
not_rules = Counter()
not_rules_examples = defaultdict(list)
totals = Counter()

def common_prefix(w1, w2):
    return len(w1) >= common_letters and len(w2) >= common_letters and w1[:common_letters] == w2[:common_letters]

def strip_prefix(w1, w2):
    while w1 and w2 and w1[0] == w2[0]:
        w1 = w1[1:]
        w2 = w2[1:]

    return w1, w2

for i, entry in enumerate(entries):
    word = entry.entry["ortografi"]
    for definition_field in definition_fields:
        for definition_path in json.expand_path(definition_field, entry.entry):
            definition = json.get_path(definition_path, entry.entry)
            for def_word in tokenize(definition):
                if word != def_word and common_prefix(word, def_word):
                    a, b = strip_prefix(word, def_word)
                    totals[a, b] += 1
                    not_rules[a, b] += 1
                    not_rules_examples[a, b].append((word, definition))

            for link in refid_re.finditer(definition):
                def_word = link.group(1).replace("_", " ")
                if word != def_word and common_prefix(word, def_word):
                    a, b = strip_prefix(word, def_word)
                    totals[a, b] += 1
                    rules[a, b] += 1
                    rules_examples[a, b].append((word, definition))

for (a, b), total_count in totals.most_common():
    count = rules[a, b]
    not_count = not_rules[(a, b)]
    if count <= 1 or not_count == 0: continue
    example, example_def = rules_examples[a, b][0]
    not_example, not_example_def = not_rules_examples[a, b][0]
    print(f'-{a} => -{b}: {count+not_count}; hv: {count}, {example}; ingen hv: {not_count}, {not_example} "{not_example_def}"')
