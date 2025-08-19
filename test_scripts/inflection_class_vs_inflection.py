from tqdm import tqdm
from collections import Counter, defaultdict
from utils.salex import is_visible, EntryWarning, SAOL, parse_böjning, entry_sort_key, entry_cell
from utils.testing import markup_cell
from dataclasses import dataclass
import re

uttal_re = re.compile(r" \[r \\\[[^\]]*\\\]\]")


@dataclass(frozen=True)
class SuspiciousInflection(EntryWarning):
    inflection: str | None
    inflection_class: str
    example_word: object # entry
    example_inflection: str | None

    def category(self):
        return f"Böjningar extra test ({self.namespace})"

    def to_dict(self):
        return super().to_dict(include_ordbok=False) | {
            "Böjningsklass": self.inflection_class,
            "Böjning": markup_cell(self.inflection or ""),
            "Exempelord i klassen": entry_cell(self.example_word, self.namespace),
            "Exempelords böjning": markup_cell(self.example_inflection or "")
        }

    def sort_key(self):
        return (self.inflection_class, entry_sort_key(self.entry, self.namespace))

    def extra_fields(self):
        return {"Exempelord i klassen", "Exempelords böjning", "Vanligast böjning i klassen"}


def lcp(s1, s2):
    """longest common prefix"""

    # NOTE for i in range(min(len(s1), len(s2))) doesn't do the same when s1 == s2.
    # This code terminates with i == len(s1) == len(s2), but a
    # range-loop would terminate with i == len(s1)-1 == len(s2)-1.
    i = 0
    while i < min(len(s1), len(s2)):
        if s1[i] != s2[i]:
            break
        i += 1
    
    return s1[:i], s1[i:], s2[i:]

def lcp_plus(s1, s2):
    candidates = []
    if s1.startswith("-"):
        candidates = [(s1[1:], s2[i:]) for i in range(len(s2)+1)]
    if s2.startswith("-"):
        candidates = [(s1[i:], s2[1:]) for i in range(len(s1)+1)]
    if s1.endswith("-"):
        candidates = [(s1[:-1], s2[:i]) for i in range(len(s2)+1)]
    if s2.endswith("-"):
        candidates = [(s1[:i], s2[:-1]) for i in range(len(s1)+1)]

    prefix, suf1, suf2 = lcp(s1, s2)
    for s1a, s2a in candidates:
        new_prefix, new_suf1, new_suf2 = lcp(s1a, s2a)
        if len(new_prefix) > len(prefix):
            prefix, suf1, suf2 = new_prefix, new_suf1, new_suf2

    return prefix, suf1, suf2

def get_inflection(entry, namespace):
    ok = True
    ortografi = entry.entry["ortografi"]
    inflection = entry.entry[namespace.path].get("böjning")
    forms = parse_böjning(entry, namespace, only_alpha=False)
    replacements = {}
    for form in forms:
        for f in form.split():
            if not f.startswith("~"):
                prefix, suffix_f, suffix_ortografi = lcp_plus(f, ortografi)
                if len(prefix) >= 3:
                    replacements[f] = f"~{suffix_ortografi}→~{suffix_f}"
                else:
                    ok = False
    for x, y in replacements.items():
        inflection = inflection.replace(x, y)
    return inflection, ok

def get_inflection(inflection, entry, namespace):
    forms = list(inflection.inflected_forms(entry, tag=True))
    replacements = {}
    word = entry.entry["ortografi"]
    böjning = entry.entry[namespace.path].get("böjning")

    for form in parse_böjning(entry, namespace, only_alpha=False):
        for f in form.split():
            if f.startswith("~"):
                test = lambda w: w == word + f[1:]
            elif f.startswith("-"):
                test = lambda w: w.endswith(f[1:])
            else:
                test = lambda w: w == f

            candidates = [tag for tag, f in forms if test(f)]
            if candidates:
                #replacements[f] = "/".join(str(i) for i in candidates)
                replacements[f] = f"[{candidates[0]}]"

    for x, y in replacements.items():
        böjning = re.sub(rf"(?<!\w){x}(?!\w)", y, böjning)

    return böjning

def test_inflection_class_vs_inflection(inflection, entries):
    by_inflection_class = defaultdict(list)
    for entry in tqdm(entries, desc="Checking inflection classes for consistency"):
        inflection_class = entry.entry.get("böjningsklass")
        if inflection_class is not None:
            by_inflection_class[inflection_class].append(entry)

    for inflection_class, entries in by_inflection_class.items():
        for namespace in [SAOL]:
            inflection_counts = Counter()
            inflection_samples = {}
            for entry in entries:
                #if entry.entry["ortografi"] == "avsvedd": breakpoint()
                if namespace.path not in entry.entry:
                    continue
                if not is_visible(namespace.path, entry.entry):
                    continue
                if entry.entry.get("ingångstyp") in ["se under", "variant", "reflexivt_verb", "partikelverb"]:
                    continue

                inflection_desc = get_inflection(inflection, entry, namespace)
                inflection_counts[inflection_desc] += 1
                if inflection_desc not in inflection_samples:
                    inflection_samples[inflection_desc] = entry

            if inflection_counts:
                expected_inflection, _ = inflection_counts.most_common(1)[0]
                sample_entry = inflection_samples[expected_inflection]

            else:
                continue

            for entry in entries:
                if namespace.path not in entry.entry:
                    continue
                if not is_visible(namespace.path, entry.entry):
                    continue
                if entry.entry.get("ingångstyp") in ["se under", "variant", "reflexivt_verb", "partikelverb"]:
                    continue

                inflection_desc = get_inflection(inflection, entry, namespace)
                if inflection_desc != expected_inflection:
                    böjning = entry.entry[namespace.path].get("böjning")
                    example = inflection_samples[expected_inflection]
                    example_böjning = example.entry[namespace.path].get("böjning")

                    yield SuspiciousInflection(entry, namespace, böjning, inflection_class, example, example_böjning)
