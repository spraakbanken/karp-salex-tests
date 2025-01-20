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


brackets = ["[]", "()", "{}", '""']
open_brackets = {s[0]: s[1] for s in brackets}
close_brackets = {s[1]: s[0] for s in brackets}


def check_caps(word):
    context = []
    result = []

    while word:
        c = word[0]
        word = word[1:]
        if c == "[" and "[" in open_brackets:
            if word.startswith("caps ") or word.startswith("rp "):
                context.append("caps")
                continue
            else:
                context.append("[")
        elif c == "]" and "]" in close_brackets:
            if not context:
                return None

            popped = context.pop()
            if popped == "caps":
                continue

        result.append(c)

    if context:
        return None
    return "".join(result)


def brackets_ok(word):
    context = []

    for c in word:
        if c in open_brackets and c in close_brackets and context and context[-1] == c:  # matching "
            context = context[:-1]

        elif c in open_brackets:
            context.append(c)

        elif c in close_brackets:
            if context and context[-1] == close_brackets[c]:
                context = context[:-1]
            else:
                return False

    return not context


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
            no_caps = check_caps(value)
            if no_caps is None or not brackets_ok(no_caps):
                # print(f"{word}, {field}:")
                # print(f"{value}")
                # print()
                writer.writerow([word, field, value])

exit()
