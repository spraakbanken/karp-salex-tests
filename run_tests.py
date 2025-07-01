from utils.testing import write_test_reports_excel, write_test_reports_html, make_test_reports
from test_scripts.ordled_agreement import test_ordled_agreement
from test_scripts.references import test_references
from test_scripts.funny_characters import test_funny_characters
from test_scripts.mismatched_brackets_etc import test_mismatched_brackets_etc
from test_scripts.suspicious_böjningar import test_böjningar
from test_scripts.field_info import test_field_info
from test_scripts.examples import test_examples
from test_scripts.saol_missing import test_saol_missing
from test_scripts.inflection_class_vs_inflection import test_inflection_class_vs_inflection
from test_scripts.particle_verbs import test_particle_verbs
from test_scripts.moderverb import test_moderverb
from test_scripts.blanksteg import test_blanksteg
from test_scripts.sorteringsform import test_sorteringsform
from test_scripts.uttal import test_uttal
from test_scripts.uttal_grammar import test_uttal_grammar
from test_scripts.empty_entries import test_empty_entries
from tqdm import tqdm
from utils.inflection import Inflection
from itertools import islice
from pathlib import Path
import typer
from functools import partial
from typing import Optional, Annotated


def func_name(func):
    if isinstance(func, partial):
        return func_name(func.func)
    else:
        return func.__name__


def main(
    output_directory: Annotated[
        Path, typer.Option("--output-directory", "-o", help="output directory", show_default=False)
    ],
    first_entry: Annotated[
        Optional[int], typer.Option(help="number of first entry to test", show_default="all")
    ] = None,
    last_entry: Annotated[Optional[int], typer.Option(help="number of last entry to test", show_default="all")] = None,
    words: Annotated[Optional[list[str]], typer.Option(help="which words to test", show_default="all")] = None,
    test: Annotated[Optional[str], typer.Option(help="which test to run", show_default="all")] = None,
):
    output_directory.mkdir(exist_ok=True)

    resource_config = resource_queries.by_resource_id("salex", expand_plugins=False).config
    entries = list(
        tqdm(
            islice(entry_queries.all_entries("salex", expand_plugins=False), first_entry, last_entry),
            desc="Reading entries",
        )
    )

    entries = [e for e in entries if "ordklass" in e.entry]

    if words is not None:
        entries = [e for e in entries if e.entry["ortografi"] in words]

    inflection = Inflection(entry_queries, entries)
    entries_by_id = {entry.id: entry for entry in entries}
    ids = {}

    tests = [
        partial(test_saol_missing, entries, inflection=inflection),
        partial(test_böjningar, entries, inflection=inflection),
        partial(test_references, entries, inflection=inflection, ids=ids),
        partial(test_field_info, resource_config, entries),
        partial(test_ordled_agreement, entries),
        partial(test_funny_characters, entries),
        partial(test_mismatched_brackets_etc, entries),
        partial(test_examples, entries, inflection=inflection),
        partial(test_inflection_class_vs_inflection, entries),
        partial(test_particle_verbs, entries),
        partial(test_moderverb, entries, ids=ids),
        partial(test_blanksteg, entries),
        partial(test_sorteringsform, entries),
        partial(test_uttal, entries),
        partial(test_uttal_grammar, entries),
        partial(test_empty_entries, entries),
    ]

    if test:
        tests = [t for t in tests if test in func_name(t)]

    warnings = []
    for t in tests:
        warnings += t()
    test_reports = make_test_reports(warnings)
    write_test_reports_excel(output_directory, test_reports)
    write_test_reports_html(output_directory, test_reports)


typer.run(main)
