"""
Support for running tests and generating warnings.

Currently writes warnings to a CSV file.
"""

from abc import abstractmethod
import pydantic
from typing import Iterator, Iterable, Self
import csv


class Warning(pydantic.BaseModel):
    entry_id: str
    ord: str

    @property
    @abstractmethod
    def identifier(self) -> object:
        raise NotImplementedError


def remove_warnings(w1, w2):
    identifiers = {w.identifier for w in w2}
    return [w for w in w1 if w.identifier not in identifiers]


def write_warnings(file, warning_cls, warnings):
    assert all(type(w) == warning_cls for w in warnings)

    writer = csv.DictWriter(file, warning_cls.model_fields.keys())
    writer.writeheader()
    for w in warnings:
        writer.writerow(w.model_dump())


def read_warnings(file, warning_cls):
    reader = csv.DictReader(file)
    return [warning_cls(**row) for row in reader]


class Tester:
    name: str
    warning_cls: type[Warning]

    @abstractmethod
    def test(self, entry) -> Iterable[Warning]:
        raise NotImplementedError()

    @classmethod
    def read_results(cls, file) -> Iterator[Warning]:
        return read_warnings(file, cls.warning_cls)

    def write_results(self, file, entries, old_warnings=[]):
        warnings = (w for e in entries for w in self.test(e))
        warnings = remove_warnings(warnings, old_warnings)
        write_warnings(file, self.warning_cls, warnings)
