"""
Support for running tests and generating warnings.

Currently writes warnings to a CSV file.
"""

from abc import abstractmethod
import pydantic
from typing import Iterator, Iterable, Self, Optional
import csv
from dataclasses import dataclass, field, replace
from functools import wraps, WRAPPER_ASSIGNMENTS, partial, lru_cache
import xlsxwriter
from xlsxwriter.format import Format
from collections import defaultdict
from warnings import warn
from pathlib import Path
import re
from utils import markup_parser
import lark

class TestWarning:
    def collection(self) -> str:
        return "Testrapporter"

    @abstractmethod
    def category(self) -> str | None:
        raise NotImplementedError

    @abstractmethod
    def to_dict(self) -> dict[str, object]:
        raise NotImplementedError

    @abstractmethod
    def sort_key(self) -> tuple[str, ...]:
        return ()


def diff_warnings(tester, w1, w2):
    identifiers = {tester.info.identifier(w) for w in w2}
    return [w for w in w1 if tester.info.identifier(w) not in identifiers]

_write_handlers = []
def add_write_handler(cls, handler):
    _write_handlers.append((cls, handler))

def add_write_via_handler(cls, transform):
    def handler(worksheet, row, col, val, cell_format=None, **kwargs):
        new_val = transform(val)
        assert type(new_val) is not type(val)
        return worksheet.write(row, col, new_val, cell_format)
    add_write_handler(cls, handler)

def add_write_class(cls):
    add_write_handler(cls, lambda worksheet, row, col, val, cell_format=None, **kwargs: val.write_cell(worksheet, row, col, cell_format, **kwargs))

@dataclass(frozen=True)
class Style:
    bold: bool = False
    underline: bool = False
    italic: bool = False
    small: bool = False
    subscript: bool = False
    superscript: bool = False

BOLD = Style(bold=True)

@dataclass
class _RichString:
    parts: list

    def write_cell(self, worksheet, row, col, cell_format, style, **kwargs):
        parts = []
        i = 0
        # Drop empty text (which is not supported by xlsxwriter).
        # We must also drop any formatting command that precedes empty text.
        # Also convert Style objects to Excel formats.
        while i < len(self.parts):
            if self.parts[i] == "":
                i += 1
            elif isinstance(self.parts[i], Format) and i+1 < len(self.parts) and self.parts[i+1] == "":
                i += 2
            else:
                part = self.parts[i]
                if isinstance(part, Style):
                    part = style(**part.__dict__)
                parts.append(part)
                i += 1

        # Single strings are not supported by xlsxwriter.
        if len(parts) == 1:
            return worksheet.write_string(row, col, parts[0], cell_format)
        elif len(parts) == 2 and isinstance(parts[0], Format):
            return worksheet.write_string(row, col, parts[1], cell_format=parts[0])

        return worksheet.write_rich_string(row, col, *parts)

add_write_class(_RichString)

def rich_string_cell(*parts):
    return _RichString(parts=parts)

def highlight(part, text):
    def find_next_match(part, text):
        if part is None:
            return None
        elif isinstance(part, re.Pattern):
            result = part.search(text)
            if result: return result.start(), result.end()
        elif isinstance(part, str):
            result = text.find(part)
            if result != -1: return result, result + len(part)
        elif isinstance(part, list) or isinstance(part, set):
            matches = [find_next_match(subpart, text) for subpart in part]
            matches = [m for m in matches if m is not None]
            if matches:
                return min(matches)
        else:
            assert False

    parts = []
    while True:
        match = find_next_match(part, text)
        if match is None: break
        start, end = match
        parts.append(text[:start])
        parts.append(BOLD)
        parts.append(text[start:end])
        text = text[end:]
    parts.append(text)
    return rich_string_cell(*parts)

def markup_cell(markup):
    try:
        tree = markup_parser.parse(markup)
    except lark.LarkError:
        return markup

    parts = []
    for fragment in markup_parser.text_fragments(markup):
        style = Style()
        for tag in fragment.tags:
            match tag:
                case "b": style = replace(style, bold=True)
                case "i": style = replace(style, italic=True)
                case "u": style = replace(style, underline=True)
                case "caps": 
                    fragment.text = fragment.text.upper()
                    style = replace(style, small=True)
                case "r": style = Style()
                case "rp": style = Style(small=True)
                case "sup": style = replace(style, superscript=True)
                case "sub": style = replace(style, subscript=True)
        parts.append(style)
        parts.append(fragment.text)

    return rich_string_cell(*parts)

def make_styler(workbook):
    styles = {
        "bold": {"bold": True},
        "underline": {"underline": True},
        "italic": {"italic": True},
        "small": {"font_size": 9},
        "subscript": {"font_script": 2},
        "superscript": {"font_script": 1},
    }

    @lru_cache(maxsize=None)
    def make_format(**kwargs):
        format = {}
        for k, v in kwargs.items():
            if v: format.update(styles[k])
        return workbook.add_format(format)

    return make_format

def write_warnings(path, warnings):
    by_workbook_and_worksheet = defaultdict(lambda: defaultdict(list))
    for w in warnings:
        book = w.collection()
        sheet = w.category()
        if sheet is not None:
            by_workbook_and_worksheet[book][sheet].append(w)

    for bookname, by_worksheet in by_workbook_and_worksheet.items():
        with xlsxwriter.Workbook(Path(path) / (bookname + ".xlsx")) as workbook:
            style = make_styler(workbook)

            for worksheet_name in sorted(by_worksheet.keys()):
                ws = by_worksheet[worksheet_name]
                ws.sort(key=lambda w: (type(w).__name__, w.sort_key()))
                ws = [w.to_dict() for w in ws]

                fields = []
                for w in ws:
                    fields += [f for f in w.keys() if f not in fields]

                worksheet = workbook.add_worksheet(worksheet_name)
                for cls, handler in _write_handlers:
                    worksheet.add_write_handler(cls, partial(handler, style=style))

                worksheet.write_row(0, 0, fields, style(bold=True))

                def write_warning(i, w):
                    worksheet.write_row(i, 0, (w.get(field) for field in fields))

                for i, w in enumerate(ws, start=1):
                    write_warning(i, w)

                worksheet.autofit()

