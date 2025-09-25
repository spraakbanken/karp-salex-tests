from utils.salex import visible_part, full_ref_regexp
from tqdm import tqdm
from karp.foundation import json
from nltk.tokenize import RegexpTokenizer
import re

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
interval = 5
common_letters = 99999999

def common_prefix(w1, w2):
    return len(w1) >= common_letters and len(w2) >= common_letters and w1[:common_letters] == w2[:common_letters]

def nearby(i, def_word):
    for j in range(i-interval, i+interval+1):
        if j in range(len(entries)) and entries[j].entry["ortografi"] == def_word:
            return True

    return False

for i, entry in enumerate(entries):
    word = entry.entry["ortografi"]
    for definition_field in definition_fields:
        for definition_path in json.expand_path(definition_field, entry.entry):
            definition = json.get_path(definition_path, entry.entry)
            for def_word in tokenize(definition):
                if word != def_word and common_prefix(word, def_word) or nearby(i, def_word):
                    print(word, "/", def_word, "/", definition)
