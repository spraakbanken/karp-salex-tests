from utils.testing import write_warnings
#from tests.ordled_agreement import test_ordled_agreement
from tests.references import test_references
from tqdm import tqdm
from functools import partial
from utils.inflection import Inflection

entries = list(tqdm(entry_queries.all_entries("salex", expand_plugins=False), desc="Reading entries"))
inflection = Inflection(entry_queries, entries)
#test_and_write_csv(test_ordled_agreement, entries, "results/ordled.new.csv", "results/ordled.old.csv")
write_warnings("results/references.new.xlsx", test_references(entries, inflection=inflection))
