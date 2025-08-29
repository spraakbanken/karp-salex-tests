from test_scripts.references import refid_re
from utils.salex import visible_part
from collections import Counter
from karp.foundation import json
from tqdm import tqdm

fields = Counter()

for entry in tqdm(entry_queries.all_entries("salex", expand_plugins=False)):
    body = visible_part(entry.entry)

    for path in json.all_paths(body):
        field = json.path_str(path, strip_positions=True)
        value = json.get_path(path, body)
        if isinstance(value, str) and refid_re.fullmatch(value):
            fields[field] += 1

for field, count in fields.most_common():
    print(field, count)
