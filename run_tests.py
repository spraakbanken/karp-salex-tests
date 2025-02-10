from tests.ordled_agreement import OrdledTester
from tqdm import tqdm

tester = OrdledTester()

entries = entry_queries.all_entries("salex", expand_plugins=False)

try:
    with open("results/ordled.old.csv", "r") as file:
        old_warnings = tester.read_results(file)
except FileNotFoundError:
    old_warnings = []

with open("results/ordled.new.csv", "w") as file:
    tester.write_results(file, tqdm(entries), old_warnings)
