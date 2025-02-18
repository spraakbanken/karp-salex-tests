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
        return "Teckeninfo"

    def category(self):
        return "Teckenstatistik"

    def to_dict(self):
        return {
            "Tecken": describe_char(self.character),
            "Frekvens": self.count
        }

@dataclass(frozen=True)
class FunnyCharacter(FieldWarning):
    funny_characters: list[str]

    def collection(self):
        return "Teckeninfo"

    def category(self):
        return "Ovanliga tecken"

    def to_dict(self):
        info = ", ".join(describe_char(chr) for chr in self.funny_characters)
        return super().to_dict() | {
            "Tecken": highlight(self.funny_characters, info)
        }

whitelist_str = '" :,[].=_()·~+|-;`´\'/\\–!∫?%®\xa0\n〈〉\xad&¦'
whitelist = set(x for x in whitelist_str)

html_entity_re = re.compile(r"&#?\w+;")

def test_funny_characters(entries):
    counter = Counter()
    for entry in tqdm(entries, desc="Finding funny characters"):
        for path in json.all_paths(entry.entry):
            if not is_visible(path, entry.entry): continue
            value = json.get_path(path, entry.entry)
            if not isinstance(value, str): continue

            funny_chars = set()
            for x in value:
                if not x.isalnum():
                    counter[x] += 1
                    if x not in whitelist: funny_chars.add(x)

            for match in html_entity_re.finditer(value):
                funny_chars.add(match.group(0))
                counter[match.group(0)] += 1

            funny_chars = list(funny_chars)
            if funny_chars:
                yield FunnyCharacter(entry, None, path, funny_chars, funny_chars)

    for x, value in counter.most_common():
        yield CharacterCount(x, value)
