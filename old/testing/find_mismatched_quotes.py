from karp.foundation import json
from collections import defaultdict, Counter
import pickle
import re
import tqdm
import csv
import sys


def shown(path, data):
    for i in range(len(path)):
        subpath = path[:i]
        subdata = json.get_path(subpath, data)

        if isinstance(subdata, dict) and "visas" in subdata and not subdata["visas"]:
            return False
    return True


def quotes_ok(word):
    matches = 0

    for i, c in enumerate(word):
        if c != "'":
            continue
        prev_char = word[i - 1] if i > 0 else ""
        next_char = word[i + 1] if i < len(word) - 1 else ""

        if prev_char.isalpha() and next_char.isalpha():
            continue  # word-inner quote

        matches += 1

    return (matches % 2) == 0


resource_config = resource_queries.by_resource_id("salex").config
entries = list(entry_queries.all_entries("salex", expand_plugins=False))
# with open("entries.pickle", "rb") as file:
#    entries = pickle.load(file)

writer = csv.writer(sys.stdout)
fields = resource_config.nested_fields()
for entry in tqdm.tqdm(entries):
    word = entry.entry.get("ortografi")
    for field in resource_config.nested_fields():
        for path in json.expand_path(field, entry.entry):
            if not shown(path, entry.entry):
                continue
            value = json.get_path(path, entry.entry)
            if not isinstance(value, str):
                continue
            if not quotes_ok(value):
                #                print(f"{word}, {field}:")
                #                print(f"{value}")
                #                print()
                writer.writerow([word, field, value])

exit()
