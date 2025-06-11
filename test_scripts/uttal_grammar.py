from utils.salex import SAOL, EntryWarning, visible_part
from utils.testing import markup_cell
from dataclasses import dataclass
from karp.foundation import json
import re
from enum import global_enum, Enum
from parsy import test_item, match_item, seq, ParseError


@dataclass(frozen=True)
class UttalWarning(EntryWarning):
    uttal: str

    def category(self):
        return f"Uttalsgrammatik ({self.namespace})"

    def to_dict(self):
        return super().to_dict() | {"Uttal": markup_cell(self.uttal)}


@global_enum
class Type(Enum):
    UTTAL = "uttal"
    PUNKTERING = "punktering"
    TYP = "typ"


@dataclass
class Token:
    type: Type
    text: str


comma = match_item(Token(type=PUNKTERING, text=","))
semicolon = match_item(Token(type=PUNKTERING, text=";"))
eller = match_item(Token(type=TYP, text="el."))
uttal = test_item(lambda tok: tok.type == UTTAL, "uttal")

grammar = seq(uttal.sep_by(comma), eller, uttal) | uttal

punkt = re.compile(r"([,;])")


def tokenise(ortografi, uttal):
    if not uttal:
        #        print("***", ortografi)
        return

    if uttal.get("typ"):
        yield Token(type=TYP, text=uttal.get("typ"))

    text = uttal["form"]
    parts = punkt.split(text)
    if parts and parts[-1] == "":
        parts = parts[:-1]
    for part in parts:
        part = part.rstrip()
        if part in {",", ";"}:
            yield Token(type=PUNKTERING, text=part)
        else:
            yield Token(type=UTTAL, text=part)


def combine_uttal(uttals):
    result = []
    for uttal in uttals:
        if uttal.get("typ"):
            result.append(uttal["typ"])
        result.append(uttal["form"])

    return " ".join(result)


def test_uttal_grammar(entries):
    for entry in entries:
        body = visible_part(entry.entry)
        ortografi = entry.entry["ortografi"]
        uttal = [json.get_path(p, body) for p in json.expand_path("saol.uttal", body)]
        if not uttal:
            continue

        tokens = [t for p in uttal for t in tokenise(ortografi, p)]
        if not tokens:
            continue

        try:
            grammar.parse(tokens)
        except ParseError:
            whole_uttal = combine_uttal(uttal)
            yield UttalWarning(entry, SAOL, whole_uttal)

    return []
