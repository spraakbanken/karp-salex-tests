from utils.testing import write_warnings
#from tests.ordled_agreement import test_ordled_agreement
from tests.references import test_references
from tqdm import tqdm
from functools import partial

inflection_rules = {
    entry.entry["name"]: entry.entry["definition"]
    for entry in tqdm(entry_queries.all_entries("inflectionrules"), desc="Reading inflection rules")
}
entries = list(tqdm(entry_queries.all_entries("salex", expand_plugins=False), desc="Reading entries"))
#test_and_write_csv(test_ordled_agreement, entries, "results/ordled.new.csv", "results/ordled.old.csv")
write_warnings("results/references.new.xlsx", test_references(entries, inflection_rules=inflection_rules))
