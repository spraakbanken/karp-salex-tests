from karp.foundation import json as karp_json
import pandas as pd
import json

problem_df = pd.read_excel("../../export/err.xlsx")
problem_ids = set(problem_df["entry_id"].tolist())

blank_ids = []
with open("empty.txt", "r") as file:
    for line in file.readlines():
        id = line.split()[0]
        blank_ids.append(id)
blank_ids = set(blank_ids)

present_ids = []
with open("../../export/out", "r") as file:
    for line in file.readlines():
        id = line.split()[0]
        present_ids.append(id)
present_ids = set(present_ids)

all_ids = set.union(problem_ids, blank_ids, present_ids)

for entry in entry_queries.all_entries("salex", expand_plugins=False):
    if entry.id not in all_ids:
        print(entry.id, entry.entry.get("ortografi"))
