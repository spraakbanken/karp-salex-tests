from karp.foundation import json
from collections import defaultdict, Counter


extra_word_classes = {
    "adjektiviskt slutled": ["adjektiv"],
    "substantiviskt slutled": ["substantiv"],
    "verbalt slutled": ["verb"],
    "adverbiellt slutled": ["adverb"],
    "substantivisk slutled": ["substantiv"],
    "substantiv ingen böjning": ["substantiv"],
    "namn": ["substantiv"],
    "s. best.": ["substantiv"],
    "räkneord": ["adjektiv", "substantiv"],
    "pronomen": ["substantiv"],
    "adj. oböjl.": ["adjektiv"],
    "rxv.": ["verb"],
    "substantiv i plural": ["substantiv"],
    "ptv.": ["verb"],
    "adv. superl.": ["adverb"],
    "adj. best. superl.": ["adjektiv"],
    "adj. superl.": ["adjektiv"],
    "adj. pl.": ["adjektiv"],
    "adv. och adj.": ["adjektiv", "adverb"],
    "s. pl. best.": ["substantiv"],
    "adv. och adj. oböjl.": ["adjektiv", "adverb"],
    "adv. komp.": ["adverb"],
    "substantiverat adj.": ["substantiv"],
    "adj. komp.": ["adjektiv"],
    "adjektiviskt förled": ["adjektiv"],
    "adj. best.": ["adjektiv"],
    "adj. komp. och adv.": ["adjektiv", "adverb"],
    "best. artikel": ["artikel"],
    "obest. artikel": ["artikel"],
    "adj": ["adjektiv"],
    "s. ": ["substantiv"],
    "pron. interr.": ["substantiv"],
    "s. pl. ": ["substantiv"],
    "v., pres.": ["verb"],
    "substantiviskt förled": ["substantiv"],
    "v., pret.": ["verb"],
    "pron. rel.": ["substantiv"],
}

# e.g. classes["41b"]["adjektiv"] = [aktiv]
inflectionclasses = defaultdict(lambda: defaultdict(list))


def word_classes(entry):
    ordklass = entry.entry.get("ordklass")
    if not ordklass:
        return
    yield ordklass
    yield from extra_word_classes.get(ordklass, [])


for entry in entry_queries.all_entries("salex"):
    ordklass = entry.entry.get("ordklass")
    böjningsklass = entry.entry.get("böjningsklass")

    if not ordklass or not böjningsklass:
        continue

    if not any([x.get("visas") for x in entry.entry.get("SAOLLemman", [])]):
        continue

    inflectionclasses[böjningsklass][ordklass].append(entry)


def number(n, sing, pl=None):
    pl = pl or sing + "s"
    return f"{n} {sing if n == 1 else pl}"


for bkl, classes in inflectionclasses.items():
    class_counts = Counter()
    for entries in classes.values():
        for entry in entries:
            for cls in word_classes(entry):
                class_counts[cls] += 1

    def is_covered(covering_classes):
        return all(
            set(word_classes(entry)) & set(covering_classes) for entries in classes.values() for entry in entries
        )

    covering_classes = set()
    for cls, _ in class_counts.most_common():
        if any(cls1 in covering_classes for cls1 in extra_word_classes.get(cls, [])):
            continue
        covering_classes.add(cls)
        if is_covered(covering_classes):
            break

    if len(covering_classes) > 1:
        print(f'{bkl} is used for {", ".join(covering_classes)}')

exit()
