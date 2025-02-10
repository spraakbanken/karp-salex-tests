from utils.testing import test_and_write_csv
from tests.ordled_agreement import test_ordled_agreement
from tqdm import tqdm

entries = tqdm(entry_queries.all_entries("salex", expand_plugins=False))
test_and_write_csv(test_ordled_agreement, entries, "results/ordled.new.csv", "results/ordled.old.csv")
