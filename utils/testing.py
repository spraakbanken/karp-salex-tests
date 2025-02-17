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
from functools import lru_cache
from collections import defaultdict
from warnings import warn

class Warning:
    @abstractmethod
    def category(self) -> str | None:
        raise NotImplementedError

    @abstractmethod
    def to_dict(self) -> dict[str, object]:
        raise NotImplementedError


def diff_warnings(tester, w1, w2):
    identifiers = {tester.info.identifier(w) for w in w2}
    return [w for w in w1 if tester.info.identifier(w) not in identifiers]

_write_handlers = []
def add_write_handler(cls, handler):
    _write_handlers.append((cls, handler))

def add_write_via_handler(cls, transform):
    def handler(worksheet, row, col, val, cell_format=None):
        new_val = transform(val)
        assert type(new_val) is not type(val)
        return worksheet.write(row, col, new_val, cell_format)
    add_write_handler(cls, handler)

def write_warnings(path, warnings):
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass

    by_worksheet = defaultdict(list)
    for w in warnings:
        sheet = w.category()
        if sheet is not None:
            by_worksheet[sheet].append(w.to_dict())

    with xlsxwriter.Workbook(path) as workbook:
        bold = workbook.add_format({'bold': True})

        for worksheet_name, ws in by_worksheet.items():
            fields = []
            for w in ws:
                fields += [f for f in w.keys() if f not in fields]

            worksheet = workbook.add_worksheet(worksheet_name)
            for cls, handler in _write_handlers:
                worksheet.add_write_handler(cls, handler)

            worksheet.write_row(0, 0, fields, bold)

            def write_warning(i, w):
                worksheet.write_row(i, 0, (w.get(field) for field in fields))

            for i, w in enumerate(ws, start=1):
                write_warning(i, w)

            worksheet.autofit()
