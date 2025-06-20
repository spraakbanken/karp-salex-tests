from utils.salex import EntryWarning, SAOL
from tqdm import tqdm
from dataclasses import dataclass


@dataclass(frozen=True)
class SorteringsFormWarning(EntryWarning):
    sorteringsform: str

    def category(self):
        return "Sorteringsformer"

    def to_dict(self):
        return super().to_dict(include_ordbok=False) | {"Sorteringsform": self.sorteringsform}


replacements = {
    " ": "",
    "-": "",
    "é": "e",
    "ê": "e",
    ":": "",
    "à": "a",
    "á": "a",
    "ü": "y",
    "(": "",
    ")": "",
    "ç": "c",
    "è": "e",
    "'": "",
    "/": "",
    ".": "",
    "œ": "oe",
    "ñ": "n",
    "ô": "o",
    "ã": "a",
    "í": "i",
    "æ": "ä",
}


def replace(x):
    for k, v in replacements.items():
        x = x.replace(k, v)
    return x


def test_sorteringsform(entries):
    for entry in tqdm(entries, desc="Checking sorteringsformer"):
        sorteringsform = entry.entry.get("sorteringsform")
        word = entry.entry.get("ortografi")

        if not sorteringsform:
            yield SorteringsFormWarning(entry, SAOL, "sorteringsform saknas")
            continue

        if not entry.entry.get("so", {}).get("visas") and not entry.entry.get("saol", {}).get("visas"):
            continue

        if any(x.isdigit() for x in word):
            continue

        if replace(word.lower()) != sorteringsform.lower().replace(" ", ""):
            yield SorteringsFormWarning(entry, SAOL, sorteringsform)
