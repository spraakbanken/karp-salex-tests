from karp.foundation import json
from tqdm import tqdm

for entry in tqdm(entry_queries.all_entries("salex", expand_plugins=False)):
    ortografi = entry.entry.get("ortografi")
    if not ortografi:
        continue
    saol = entry.entry.get("saol")
    if not saol:
        continue
    o2 = saol.get("ortografi")
    if not o2:
        continue
    if ortografi != o2:
        print(entry.id, ortografi, o2)

exit()
