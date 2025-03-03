"""
Support for running tests and generating warnings.

Currently writes warnings to a CSV file.
"""

from abc import abstractmethod
from dataclasses import dataclass, replace
from functools import partial, lru_cache
import xlsxwriter
from xlsxwriter.format import Format
from collections import defaultdict
from pathlib import Path
import re
from utils import markup_parser
import lark
from jinja2 import Environment, FileSystemLoader, select_autoescape
import html


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


_write_classes = set()
_write_vias = {}


def _add_write_handlers(worksheet, **kwargs):
    for cls in _write_classes:
        worksheet.add_write_handler(
            cls,
            lambda worksheet, row, col, val, cell_format=None: val.write_cell(
                worksheet, row, col, cell_format, **kwargs
            ),
        )

    for cls, transform in _write_vias.items():

        def handler(worksheet, row, col, val, cell_format=None, transform=None):
            new_val = transform(val)
            assert type(new_val) is not type(val)
            return worksheet.write(row, col, new_val, cell_format)

        worksheet.add_write_handler(cls, partial(handler, transform=transform))


def add_write_via_handler(cls, transform):
    _write_vias[cls] = transform


def add_write_class(cls):
    _write_classes.add(cls)


add_write_via_handler(type(None), lambda x: "")
add_write_via_handler(bool, lambda x: "ja" if x else "nej")
add_write_via_handler(int, str)
add_write_via_handler(bool, str)


@dataclass(frozen=True)
class Style:
    bold: bool = False
    underline: bool = False
    italic: bool = False
    small: bool = False
    subscript: bool = False
    superscript: bool = False


def style_to_html(style, end=False):
    tags = []
    if style.bold:
        tags.append("b")
    if style.underline:
        tags.append("u")
    if style.italic:
        tags.append("i")
    if style.small:
        tags.append("small")
    if style.subscript:
        tags.append("sub")
    if style.subscript:
        tags.append("sup")

    result = []
    if end:
        for tag in reversed(tags):
            result.append(f"</{tag}>")
    else:
        for tag in tags:
            result.append(f"<{tag}>")

    return "".join(result)


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
            elif isinstance(self.parts[i], Style) and i + 1 < len(self.parts) and self.parts[i + 1] == "":
                i += 2
            else:
                part = self.parts[i]
                if isinstance(part, Style):
                    part = style(**part.__dict__)
                parts.append(part)
                i += 1

        # Single strings are not supported by xlsxwriter.
        if len(parts) == 0:
            return worksheet.write_blank(row, col, cell_format)
        elif len(parts) == 1:
            return worksheet.write_string(row, col, parts[0], cell_format)
        elif len(parts) == 2 and isinstance(parts[0], Format):
            return worksheet.write_string(row, col, parts[1], cell_format=parts[0])

        return worksheet.write_rich_string(row, col, *parts)

    def render_html(self):
        result = []
        i = 0
        while i < len(self.parts):
            if isinstance(self.parts[i], Style) and i + 1 < len(self.parts):
                style = self.parts[i]
                result += style_to_html(style, end=False)
                result.append(render_html(self.parts[i + 1]))
                result += style_to_html(style, end=True)
                i += 2
            elif isinstance(self.parts[i], Style):
                i += 1
            else:
                result += render_html(self.parts[i])
                i += 1

        return "".join(result)


add_write_class(_RichString)


def rich_string_cell(*parts):
    return _RichString(parts=parts)


def highlight(part, text, case_sensitive=True):
    flags = 0 if case_sensitive else re.IGNORECASE

    def find_next_match(part, text):
        if part is None:
            return None
        elif isinstance(part, re.Pattern):
            result = part.search(text, flags)
            if result:
                return result.start(), result.end()
        elif isinstance(part, str):
            if case_sensitive:
                result = text.find(part)
            else:
                result = text.lower().find(part.lower())
            if result != -1:
                return result, result + len(part)
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
        if match is None:
            break
        start, end = match
        parts.append(text[:start])
        parts.append(BOLD)
        parts.append(text[start:end])
        text = text[end:]
    parts.append(text)
    return rich_string_cell(*parts)


def markup_cell(markup):
    try:
        _tree = markup_parser.parse(markup)
    except lark.LarkError:
        return markup

    parts = []
    for fragment in markup_parser.text_fragments(markup):
        style = Style()
        for tag in fragment.tags:
            match tag:
                case "b":
                    style = replace(style, bold=True)
                case "i":
                    style = replace(style, italic=True)
                case "u":
                    style = replace(style, underline=True)
                case "caps":
                    fragment.text = fragment.text.upper()
                    style = replace(style, small=True)
                case "r":
                    style = Style()
                case "rp":
                    style = Style(small=True)
                case "sup":
                    style = replace(style, superscript=True)
                case "sub":
                    style = replace(style, subscript=True)
        parts.append(style)
        parts.append(fragment.text)

    return rich_string_cell(*parts)


@dataclass
class _Link:
    text: object
    url: str

    def write_cell(self, worksheet, row, col, cell_format, **kwargs):
        return worksheet.write_url(row, col, self.url, cell_format, self.text)

    def render_html(self):
        return f'<a href="{html.escape(self.url)}">{render_html(self.text)}</a>'


add_write_class(_Link)


def link_cell(text, url):
    return _Link(text, url)


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
            if v:
                format.update(styles[k])
        return workbook.add_format(format)

    return make_format


@dataclass
class TestReport:
    fields: list[str]
    rows: list[list[object]]


def make_test_report(warnings) -> TestReport:
    warnings.sort(key=lambda w: (type(w).__name__, w.sort_key()))
    warnings = [w.to_dict() for w in warnings]

    fields = []
    for w in warnings:
        fields += [f for f in w.keys() if f not in fields]

    rows = []
    for w in warnings:
        rows.append([w.get(field) for field in fields])

    return TestReport(fields=fields, rows=rows)


def make_test_reports(warnings) -> dict[str, dict[str, TestReport]]:
    by_collection_and_category = defaultdict(lambda: defaultdict(list))
    for w in warnings:
        collection = w.collection()
        category = w.category()
        if collection is not None and category is not None:
            by_collection_and_category[collection][category].append(w)

    def sorted_dict(d):
        keys = list(d)
        return {k: d[k] for k in sorted(keys)}

    return {
        collection: {category: make_test_report(warnings) for category, warnings in sorted_dict(by_category).items()}
        for collection, by_category in sorted_dict(by_collection_and_category).items()
    }


def write_test_reports_excel(path, test_reports):
    for bookname, by_worksheet in test_reports.items():
        with xlsxwriter.Workbook(Path(path) / (bookname + ".xlsx")) as workbook:
            style = make_styler(workbook)

            for worksheet_name, report in by_worksheet.items():
                worksheet = workbook.add_worksheet(worksheet_name)
                _add_write_handlers(worksheet, style=style)

                worksheet.write_row(0, 0, report.fields, style(bold=True))

                for i, w in enumerate(report.rows, start=1):
                    worksheet.write_row(i, 0, w)

                worksheet.autofit()


# TODO: use PackageLoader instead
template_path = Path(__file__).parent.parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(template_path), autoescape=select_autoescape())


def render_html(value):
    if isinstance(value, str):
        return html.escape(value)
    elif type(value) in _write_vias:
        return render_html(_write_vias[type(value)](value))
    elif type(value) in _write_classes:
        return value.render_html()
    else:
        return render_html(str(value))


def write_test_reports_html(path, test_reports):
    for title, by_table in test_reports.items():
        template = jinja_env.get_template("test_report.html")

        for test_report in by_table.values():
            test_report.rows = [[render_html(cell) for cell in row] for row in test_report.rows]

        with open(Path(path) / (title + ".html"), "w") as out_file:
            out_file.write(template.render(title=title, test_reports=by_table))
