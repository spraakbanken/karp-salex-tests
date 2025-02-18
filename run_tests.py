from utils.testing import write_warnings
from tests.ordled_agreement import test_ordled_agreement
from tests.references import test_references
from tests.funny_characters import test_funny_characters
from tests.mismatched_brackets_etc import test_mismatched_brackets_etc
from tqdm import tqdm
from functools import partial
from utils.inflection import Inflection
from itertools import islice

#entry_start = 100000
#entry_stop = 110000
entry_start = None
entry_stop = None

entries = list(tqdm(islice(entry_queries.all_entries("salex", expand_plugins=False), entry_start, entry_stop), desc="Reading entries"))
inflection = Inflection(entry_queries, entries)

warnings = []
warnings += test_ordled_agreement(entries)
warnings += test_references(entries, inflection=inflection)
warnings += test_funny_characters(entries)
warnings += test_mismatched_brackets_etc(entries)
write_warnings("results", warnings)
