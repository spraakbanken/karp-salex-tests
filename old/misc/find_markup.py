from collections import Counter
from utils import markup_parser
from karp.foundation import json
import lark
from tqdm import tqdm

counts = Counter()

def is_plain_text(tree):
    for fragment in markup_parser.text_fragments(tree):
        if fragment.tags:
            return False
    return True

for entry in tqdm(entry_queries.all_entries("salex", expand_plugins=False)):
    for path in json.all_paths(entry.entry):
        value = json.get_path(path, entry.entry)
        if not isinstance(value, str): continue

        try:
            tree = markup_parser.parse(value)
            if not is_plain_text(tree):
                if json.path_str(path, strip_positions=True) == "so.huvudbetydelser.definition": print(entry.id, entry.entry["ortografi"], value)
                counts[json.path_str(path, strip_positions=True)] += 1
        except lark.LarkError:
            pass

for field, count in counts.most_common():
    print(field, count)
