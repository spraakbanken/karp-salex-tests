from karp.foundation import json
from collections import defaultdict
from utils.salex import find_ids, find_refs, entry_name, is_visible, SO, SAOL, Id, IdLocation, parse_ref, TEXT, TextId, variant_fields, EntryWarning, entry_cell
from dataclasses import dataclass
from tqdm import tqdm
import re
from karp.plugins.inflection_plugin import apply_rules
from karp.lex.domain.dtos import EntryDto

refid_re = re.compile(r"\+([^ +]*)\(refid=([a-zA-Z0-9]*)\)(?!\(refid=)")
id_re = re.compile(r"(?:x|l|kc)nr[a-zA-Z0-9]+")
only_refid_re = re.compile(r"refid")
plus_re = re.compile(r"\+(?=\w)(?!verb)")

def match_contains(m1, m2):
    return m1.start() <= m2.start() and m1.end() >= m2.end()

@dataclass(frozen=True)
class DuplicateId(EntryWarning):
    entry2: EntryDto
    id: Id

    def _is_missing_homografnr(self):
        return self.id.type == TEXT and not self.id.id.homografNr

    def category(self):
        if self._is_missing_homografnr():
            return f"Homografnummer saknas ({self.namespace})"
        else:
            return f"Duplicate id ({self.namespace})"

    def to_dict(self):
        result = {
            "Ord": entry_cell(self.entry, self.namespace),
            "Ord 2": entry_cell(self.entry2, self.namespace)
        }
        if not self._is_missing_homografnr():
            result["Id"] = self.id
        return result

def test_references(entries, inflection_rules):
    ids = {}
    ids_without_homografNr = set()

    def warning(kind, ref, loc):
        return {
            "ord": entry_name(loc.entry, ref.namespace),
            "fält": json.path_str(loc.path, strip_positions=True),
            "hänvisning": loc.text,
            "hänvisat ord": entry_name(ids[ref].entry, ref.namespace) if ref in ids else "?",
            "feltyp": kind,
        }

    def better(ref, source1, source2):
        body1 = source1.entry.entry.get(ref.namespace.path)
        body2 = source2.entry.entry.get(ref.namespace.path)
        if body1 and not body2: return True
        if not body1: return False
        return not body2.get("visas", True) # if both are hidden pick arbitrarily

    for e in tqdm(entries, desc="Finding IDs"):
        for id, source in find_ids(e):
            if id in ids:
                if better(id, source, ids[id]):
                    ids[id] = source
                elif better(id, ids[id], source):
                    pass
                else:
                    yield DuplicateId(namespace=id.namespace, entry=ids[id].entry, entry2=e, id=id)

            else:
                ids[id] = source

    return
    # Check for missing homografNr
    for id, source in ids.items():
        if id.type == TEXT:
            if id.id.homografNr is not None:
                banned_id = Id(id.namespace, id.type, TextId(id.id.ortografi, None))
                if banned_id in ids:
                    if source.entry.entry[id.namespace.path].get("visas", True) and \
                        ids[banned_id].entry.entry[id.namespace.path].get("visas", True):
                        yield warning("homografNr saknas", banned_id, ids[banned_id])
                ids_without_homografNr.add(banned_id)

    # Check for unnecessary homografNr:
    by_homografNr = defaultdict(set)
    for id, source in ids.items():
        if id.type == TEXT and id.id.homografNr is not None and source.entry.entry[id.namespace.path].get("visas", True):
            by_homografNr[id.namespace, id.id.ortografi].add(id.id.homografNr)

    for (namespace, ortografi), homografNrs in by_homografNr.items():
        if len(homografNrs) == 1:
            yield {"ord": ortografi, "fält": str(namespace), "hänvisning": "", "hänvisat ord": "", "feltyp": f"onödig homografNr {homografNrs}"}
        elif list(sorted(homografNrs)) != list(range(1, len(homografNrs)+1)):
            yield {"ord": ortografi, "fält": str(namespace), "hänvisning": "", "hänvisat ord": "", "feltyp": f"ogiltiga homografNr {homografNrs}"}

    for entry in tqdm(entries, desc="Checking references"):
        for ref, loc in find_refs(entry):
            if not loc.visible: continue

            if ref not in ids:
                if ref in ids_without_homografNr:
                    yield warning("homografNr saknas i referens", ref, loc)
                else:
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
                    loc = IdLocation(entry, [namespace.path] + path, ref.group(0))
                    word = ref.group(1).replace("_", " ")
                    target = ref.group(2)
                    kind, ref = parse_ref(None, target)
                    id = Id(namespace, kind, ref)
                    target_entry = ids[id].entry
                    target_word = target_entry.entry["ortografi"]
                    target_body = target_entry.entry.get(namespace.path, {})

                    if word == target_word: continue
                    # Check to see if we find it in a variant form
                    variant_forms = [
                        json.get_path(path, target_body)
                        for field in variant_fields[namespace]
                        for path in json.expand_path(field, target_body)
                    ]
                    if word in variant_forms: continue

                    # Check to see if we find it as an inflected form
                    inflection_class = target_entry.entry.get("böjningsklass")
                    cases = inflection_rules.get(inflection_class, [])
                    if word not in [apply_rules(w, case["rules"]) for w in [target_word, *variant_forms] for case in cases]:
                        # TODO: report mistakenly pointing at variant
                        # form as a minor error?
                        yield warning("hänvisning pekar på oväntat ord", id, loc)
