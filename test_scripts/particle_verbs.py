from utils.salex import EntryWarning, SAOL
from tqdm import tqdm
from dataclasses import dataclass


@dataclass(frozen=True)
class ParticleVerbWarning(EntryWarning):
    info: str

    def category(self):
        return f"Partikelverb ({self.namespace})"

    def to_dict(self):
        return super().to_dict(include_ordbok=False) | {"Info": self.info}


particles = {
    "an",
    "av",
    "bakom",
    "bi",
    "bort",
    "dit",
    "efter",
    "emellan",
    "emot",
    "fast",
    "fram",
    "för",
    "förbi",
    "före",
    "hem",
    "hemma",
    "hän",
    "i",
    "ifråga",
    "ifrån",
    "igen",
    "igenom",
    "igång",
    "ihop",
    "ihåg",
    "in",
    "inne",
    "itu",
    "iväg",
    "kvar",
    "loss",
    "lös",
    "med",
    "mot",
    "ner",
    "nere",
    "om",
    "på",
    "runt",
    "samman",
    "sig",
    "till",
    "undan",
    "under",
    "upp",
    "uppe",
    "ur",
    "ut",
    "ute",
    "vid",
    "åt",
    "åter",
    "över",
    "överens",
}


def test_particle_verbs(entries):
    for entry in tqdm(entries, desc="Checking particle verbs"):
        if entry.entry.get("ingångstyp") not in ["partikelverb", "reflexivt_verb"]:
            continue

        sorteringsform = entry.entry.get("sorteringsform")
        word = entry.entry.get("ortografi")
        orig_word = word

        while any(word.endswith(" " + p) for p in particles):
            for p in particles:
                if word.endswith(" " + p):
                    word = word[: -len(p) - 1]

        if not sorteringsform:
            yield ParticleVerbWarning(entry, SAOL, f"missing sorteringsform: {sorteringsform}")

        if sorteringsform and orig_word != sorteringsform:
            yield ParticleVerbWarning(entry, SAOL, f"misstänkt sorteringsform: {sorteringsform}")

        elif " " not in orig_word or " " in word or word == orig_word:
            yield ParticleVerbWarning(entry, SAOL, f"misstänkt ortografi: {word}")
