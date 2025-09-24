from karp.foundation import json
from utils.salex import FieldWarning, is_visible
from utils.testing import highlight, TestWarning
from dataclasses import dataclass
import unicodedata
import re
from collections import Counter
from tqdm import tqdm


def describe_char(x):
    if len(x) == 1:
        return f"U{ord(x):04X} {x} ({unicodedata.name(x, 'UNKNOWN')})"
    elif x.startswith("&"):
        return f"{x} (HTML entity)"
    else:
        return x


@dataclass(frozen=True)
class CharacterCount(TestWarning):
    character: str
    count: int

    def collection(self):
        return "Teckenstatistik"

    def category(self):
        return "Teckenstatistik"

    def to_dict(self):
        return {"Tecken": describe_char(self.character), "Frekvens": self.count}


@dataclass(frozen=True)
class FunnyCharacter(FieldWarning):
    funny_characters: list[str]
    html: bool

    def collection(self):
        if self.html:
            return "Teckenstatistik"
        else:
            return "Testrapporter"

    def category(self):
        return "Specialtecken"

    def to_dict(self):
        info = ", ".join(describe_char(chr) for chr in self.funny_characters)
        return super().to_dict() | {"Tecken": highlight(self.funny_characters, info)}


whitelist_str = "\" :,[].=_()·~+|-;`´'/\\–!∫?%®\xa0\n〈〉\xad&¦"
whitelist = set(x for x in whitelist_str)

html_entity_re = re.compile(r"&#?\w+;")


def test_funny_characters(entries):
    counter = Counter()
    for entry in tqdm(entries, desc="Finding funny characters"):
        #for path in list(x for field in ["so.böjning", "so.variantformer.böjning", "saol.böjning", "saol.variantformer.böjning"] for x in json.expand_path(field, entry.entry)):
        for path in list(x for field in ["so.böjning", "so.variantformer.böjning"] for x in json.expand_path(field, entry.entry)):
            if "fonetikparentes" in path:
                continue

            if not is_visible(path, entry.entry):
                continue
            value = json.get_path(path, entry.entry)
            if not isinstance(value, str):
                continue

            funny_chars = set()
            html = False
            for x in value:
                if not x.isalnum():
                    counter[x] += 1
                    if x not in whitelist:
                        funny_chars.add(x)

            for match in html_entity_re.finditer(value):
                funny_chars.add(match.group(0))
                counter[match.group(0)] += 1
                html = True

            funny_chars = list(funny_chars)
            if funny_chars:
                yield FunnyCharacter(entry, None, path, funny_chars, funny_chars, html)

    for x, value in counter.most_common():
        yield CharacterCount(x, value)
