from karp.foundation import json
from collections import defaultdict, Counter


def flatten_list(x):
    if isinstance(x, list):
        for y in x:
            yield from flatten_list(y)
    else:
        yield x


def get_values_of(path, data):
    if json.has_path(path, data):
        yield from flatten_list(json.get_path(path, data))


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
    "adv. komp": ["adverb"],
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


def word_classes(entry):
    ordklass = entry.entry.get("ordklass")
    if not ordklass:
        return
    yield ordklass
    yield from extra_word_classes.get(ordklass, [])


# e.g. examples["en .. film"]["substantiv"] = [nyskapande]
examples = defaultdict(lambda: defaultdict(list))


def normalised_examples(entry):
    for saol_lemma in get_values_of("SAOLLemman", entry.entry):
        if not saol_lemma.get("visas"):
            continue
        ortografi = saol_lemma["ortografi"].lower()
        for lexeme in get_values_of("lexem", saol_lemma):
            for example in get_values_of("exempel", lexeme):
                example_text = json.get_path("text", example).lower()
                replacements = [(ortografi[0] + ".", "X"), (ortografi, "X")]

                if "verb" in word_classes(entry) and ortografi.endswith("a"):
                    replacements += [
                        (ortografi[:-1] + "er", "Xr"),
                        (ortografi[:-1] + "te", "Xde"),
                        (ortografi[:-1] + "t", "Xt"),
                        (ortografi[:-1] + "de", "Xde"),
                        (ortografi[:-1] + "d", "Xd"),
                        (ortografi[:-1] + "s", "Xs"),
                    ]

                if "substantiv" in word_classes(entry):
                    if ortografi.endswith("a"):
                        replacements += [(ortografi[:-1] + "or", "Xr")]
                    elif ortografi.endswith("e"):
                        replacements += [("Xt", "Xn"), ("Xna", "Xrna")]
                    else:
                        replacements += [("Xer", "Xr"), ("Xar", "Xr")]

                if "adjektiv" in word_classes(entry):
                    if ortografi.endswith("d"):
                        replacements += [(ortografi[:-1] + "t", "Xt")]

                for before, after in replacements:
                    example_text = example_text.replace(before, after)
                yield example_text


for entry in entry_queries.all_entries("salex"):
    ordklass = entry.entry.get("ordklass")
    if not ordklass:
        continue
    for example in normalised_examples(entry):
        examples[example][ordklass].append(entry)


def number(n, sing, pl=None):
    pl = pl or sing + "s"
    return f"{n} {sing if n == 1 else pl}"


for example, classes in examples.items():
    class_counts = Counter()
    for entries in classes.values():
        for entry in entries:
            for cls in word_classes(entry):
                class_counts[cls] += 1
    _, max_count = class_counts.most_common(1)[0]
    most_common_classes = {cls for cls, count in class_counts.items() if count == max_count}

    problematic_cases = []
    for cls, entries in classes.items():
        if cls in most_common_classes:
            continue
        for entry in entries:
            if most_common_classes & set(word_classes(entry)):
                continue

            problematic_cases.append(entry)

    if problematic_cases:
        print(f'{example}: appears {number(max_count, "time")} as {next(iter(most_common_classes))} but also as:')

        for entry in problematic_cases:
            word = entry.entry.get("ortografi")
            word_class = entry.entry.get("ordklass")
            print(f"  {word_class}: {word}")

        print()

exit()
