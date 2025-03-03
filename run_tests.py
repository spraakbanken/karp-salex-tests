from utils.testing import write_test_reports_excel, write_test_reports_html, make_test_reports
from tests.ordled_agreement import test_ordled_agreement
from tests.references import test_references
from tests.funny_characters import test_funny_characters
from tests.mismatched_brackets_etc import test_mismatched_brackets_etc
from tests.suspicious_böjningar import test_böjningar
from tests.field_info import test_field_info
from tests.examples import test_examples
from tests.saol_missing import test_saol_missing
from tqdm import tqdm
from utils.inflection import Inflection
from itertools import islice
from pathlib import Path

top_dir = Path(__file__).parent
results_dir = top_dir / "results"
results_dir.mkdir(exist_ok=True)

test_on_subset = False
if test_on_subset:
    entry_start = 100000
    entry_stop = 110000
else:
    entry_start = None
    entry_stop = None

resource_config = resource_queries.by_resource_id("salex", expand_plugins=False).config
entries = list(
    tqdm(
        islice(entry_queries.all_entries("salex", expand_plugins=False), entry_start, entry_stop),
        desc="Reading entries",
    )
)
inflection = Inflection(entry_queries, entries)
entries_by_id = {entry.id: entry for entry in entries}
ids = {}

warnings = []
warnings += test_saol_missing(entries, inflection=inflection)
warnings += test_böjningar(entries, inflection=inflection)
warnings += test_references(entries, inflection=inflection, ids=ids)
warnings += test_field_info(resource_config, entries)
warnings += test_ordled_agreement(entries)
warnings += test_funny_characters(entries)
warnings += test_mismatched_brackets_etc(entries)
warnings += test_examples(entries, inflection=inflection)
test_reports = make_test_reports(warnings)
write_test_reports_excel(top_dir / "results", test_reports)
write_test_reports_html(top_dir / "results", test_reports)
