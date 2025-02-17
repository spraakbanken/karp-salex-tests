"""
Support for running tests and generating warnings.

Currently writes warnings to a CSV file.
"""

from abc import abstractmethod
import pydantic
from typing import Iterator, Iterable, Self, Optional
import csv
from dataclasses import dataclass, field
from functools import wraps, WRAPPER_ASSIGNMENTS
import xlsxwriter
import os

@dataclass
class FieldInfo:
    priority: int
    info: bool

    def combine(self, other: Self):
        return FieldInfo(priority=min(self.priority, other.priority), info=self.info or other.info)

@dataclass
class TesterInfo:
    field_info: dict[str, FieldInfo] = field(default_factory = dict)

    def add_field(self, field, info: FieldInfo):
        if field in self.field_info:
            info = info.combine(self.field_info[field])
        self.field_info[field] = info

    @property
    def id_fields(self):
        return [f for f, info in self.field_info.items() if not info.info]

    @property
    def fields(self):
        result = list(self.field_info)
        result.sort(key=lambda f: self.field_info[f].priority)
        return result

    def identifier(self, w):
        return tuple((field, w[field]) for field in sorted(self.id_fields))


def annotate_tester(tester):
    if not hasattr(tester, "info"):
        tester.info = TesterInfo()


def fields(*args, info=False, priority=0):
    def inner(tester):
        annotate_tester(tester)
        for arg in args:
            tester.info.add_field(arg, FieldInfo(info=info, priority=priority))
        return tester
    return inner


def annotate_entry(entry, w):
    return {"id": entry.id, "ortografi": entry.entry["ortografi"], **w}


def per_entry(tester):
    annotate_tester(tester)

    @fields("id", "ortografi", priority=-10)
    @wraps(tester, assigned=WRAPPER_ASSIGNMENTS + ("info",))
    def inner(entries, **kwargs):
        for entry in entries:
            for w in tester(entry.entry, **kwargs):
                yield annotate_entry(entry, w)

    return inner


def diff_warnings(tester, w1, w2):
    identifiers = {tester.info.identifier(w) for w in w2}
    return [w for w in w1 if tester.info.identifier(w) not in identifiers]


def write_warnings(file, tester, warnings):
    annotate_tester(tester)
    writer = csv.DictWriter(file, tester.info.fields)
    writer.writeheader()
    for w in warnings:
        writer.writerow(w)


def read_warnings(file):
    reader = csv.DictReader(file)
    return list(reader)


def test_and_write_csv(tester, entries, path, old_path=None, **kwargs):
    if old_path:
        try:
            with open(old_path, "r") as file:
                old_warnings = read_warnings(file)
        except FileNotFoundError:
            old_warnings = []

    all_warnings = tester(entries, **kwargs)
    new_warnings = diff_warnings(tester, all_warnings, old_warnings)

    try:
        os.unlink(path)
    except FileNotFoundError:
        pass
    with xlsxwriter.Workbook(path) as workbook:
        worksheet = workbook.add_worksheet()

        def write_warning(i, w):
            worksheet.write_row(i+1, 0, (w.get(field, "") for field in tester.info.fields))

        annotate_tester(tester)
        worksheet.write_row(0, 0, tester.info.fields)
        for i, w in enumerate(new_warnings):
            write_warning(i, w)


#    with open(path, "w") as file:
#        write_warnings(file, tester, new_warnings)
