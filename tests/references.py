from karp.foundation import json
from collections import defaultdict
from utils.salex import find_ids, find_refs, entry_name, is_visible, SO, SAOL, Id, IdLocation, parse_ref
from utils.testing import fields
from dataclasses import dataclass
from tqdm import tqdm
import re
from karp.plugins.inflection_plugin import apply_rules

refid_re = re.compile(r"\+([^ +]*)\(refid=([a-zA-Z0-9]*)\)(?!\(refid=)")
id_re = re.compile(r"(?:x|l|kc)nr[a-zA-Z0-9]+")
only_refid_re = re.compile(r"refid")
plus_re = re.compile(r"\+(?=\w)(?!verb)")

def match_contains(m1, m2):
    return m1.start() <= m2.start() and m1.end() >= m2.end()

@fields("ord", "fält", "hänvisning", "hänvisat ord", "feltyp")
def test_references(entries, inflection_rules):
    ids = {}

    def warning(kind, ref, loc):
        return {
            "ord": entry_name(loc.entry, ref.namespace),
            "fält": json.path_str(loc.path, strip_positions=True),
            "hänvisning": loc.text,
            "hänvisat ord": entry_name(ids[ref].entry, ref.namespace) if ref in ids else "?",
            "feltyp": kind,
        }

    for e in tqdm(entries, desc="Finding IDs"):
        for id, source in find_ids(e):
            if id in ids:
                yield warning("duplikat id", id, source)
            ids[id] = source

    for entry in tqdm(entries, desc="Checking references"):
        for ref, loc in find_refs(entry):
            if not loc.visible: continue

            if ref not in ids:
                yield warning("hänvisat ord inte hittat", ref, loc)

            elif not ids[ref].visible:
                yield warning("hänvisning till förrådat ord", ref, loc)

        # Check +hund(refid=lnr123456)-style references
        for namespace in [SO, SAOL]:
            body = entry.entry.get(namespace.path, {})
            for path in json.all_paths(body):
                if not is_visible(path, body): continue
                value = json.get_path(path, body)
                if not isinstance(value, str): continue

                references = list(refid_re.finditer(value))

                # Check for references with bad syntax
                tests = [
                    (only_refid_re, "only_refid felaktig referenssyntax - använd +XXX(refid=YYY)"),
                    (plus_re, "plus felaktig referenssyntax - använd +XXX(refid=YYY)"),
                ]
                if "hänvisning" not in path:
                    tests.append((id_re, "id felaktig referenssyntax - använd +XXX(refid=YYY)"))

                loc = IdLocation(entry, [namespace.path] + path, value)
                for regexp, message in tests:
                    for maybe_ref in regexp.finditer(value):
                        if not any(match_contains(ref, maybe_ref) for ref in references):
                            yield warning(message, Id(type=None, id=None, namespace=namespace), loc)

                # Check that target of reference is correct
                for ref in references:
                    word = ref.group(1).replace("_", " ")
                    target = ref.group(2)
                    kind, ref = parse_ref(None, target)
                    id = Id(namespace, kind, ref)
                    target_entry = ids[id].entry
                    target_word = target_entry.entry["ortografi"]
                    if word != target_word:
                        # Check all inflection rules
                        inflection_class = target_entry.entry.get("böjningsklass")
                        cases = inflection_rules.get(inflection_class, [])
                        if word not in [apply_rules(target_word, case["rules"]) for case in cases]:


                            yield warning("hänvisning pekar på oväntat ord", id, loc)
