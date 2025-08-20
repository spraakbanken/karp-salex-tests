from tqdm import tqdm
from collections import defaultdict
from utils.salex import is_visible
from karp.plugins.inflection_plugin import apply_rules, RuleNotPossible


class Inflection:
    def __init__(self, entry_queries, entries):
        self.inflection_rules = {
            entry.entry["name"]: entry.entry["definition"]
            for entry in tqdm(entry_queries.all_entries("inflectionrules"), desc="Reading inflection rules")
        }

        # Fetch inflection class from SAOL where a lemma is SO-only
        saol = defaultdict(set)
        so = defaultdict(set)

        for entry in entries:
            entry = entry.entry

            for namespace, other_namespace, dict in [("saol", "so", saol), ("so", "saol", so)]:
                if (
                    namespace in entry
                    and is_visible(namespace, entry)
                    and other_namespace not in entry
                    and "böjningsklass" in entry
                ):
                    word_class = entry["ordklass"]
                    if word_class == "ptv.":
                        word_class = "verb"
                    dict[entry["ortografi"], word_class].add(entry["böjningsklass"])

        self.extra_inflection_classes = {k: v for k, v in saol.items() if k in so}

    def inflected_forms(self, entry, word=None, tag=False):
        headword = entry.entry["ortografi"]
        word_class = entry.entry["ordklass"]
        if word_class == "ptv.":
            word_class = "verb"

        if word is None:
            word = headword

        if entry.entry["ingångstyp"] in ["partikelverb", "reflexivt_verb"]:
            suffix = word.split()[1:]
            word = word.split()[0]
        else:
            suffix = []

        inflection_classes = {entry.entry.get("böjningsklass")}
        inflection_classes.update(self.extra_inflection_classes.get((word, word_class), set()))
        inflection_classes.update(self.extra_inflection_classes.get((headword, word_class), set()))

        for inflection_class in inflection_classes:
            for case in self.inflection_rules.get(inflection_class, []):
                try:
                    applied = apply_rules(word, case["rules"])
                    glued = " ".join([applied] + suffix)
                    if tag:
                        yield (case["tagg"], glued)
                    else:
                        yield glued
                except RuleNotPossible:
                    pass
