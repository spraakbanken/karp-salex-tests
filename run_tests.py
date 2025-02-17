from utils.testing import write_warnings
from tests.ordled_agreement import test_ordled_agreement
from tests.references import test_references
from tqdm import tqdm
from functools import partial
from utils.inflection import Inflection

entries = list(tqdm(entry_queries.all_entries("salex", expand_plugins=False), desc="Reading entries"))
inflection = Inflection(entry_queries, entries)

warnings = []
warnings += test_ordled_agreement(entries)
warnings += test_references(entries, inflection=inflection)
write_warnings("Testresultat.xlsx", warnings)
