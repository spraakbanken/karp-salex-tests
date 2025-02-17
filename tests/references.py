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

    def category(self):
        return f"Duplicate id ({self.namespace})"

    def to_dict(self):
        return {
            "Ord": entry_cell(self.entry, self.namespace),
            "Ord 2": entry_cell(self.entry2, self.namespace),
            "Id": self.id
        }

@dataclass(frozen=True)
class HomografWrong(Warning):
    namespace: str
    ortografi: str
    homografer: list[IdLocation]
    message: str

    def category(self):
        return f"Felaktiga homografnummer ({self.namespace})"

    def to_dict(self):
        result = {"Ord": self.ortografi, "Fel": self.message}
        for i, homograf in enumerate(self.homografer, start=1):
            result[f"Homograf {i}"] = homograf
        return result

def test_references(entries, inflection_rules):
    ids = {}
    by_ortografi: dict[tuple[Namespace, str], list[Id]] = defaultdict(list)

    # Read in all IDs and check for duplicates
    for e in tqdm(entries, desc="Finding IDs"):
        for id, source in find_ids(e):
            if id in ids:
                if source.visible and not ids[id].visible:
                    ids[id] = source
                elif not source.visible:
                    pass
                elif not (id.type == TEXT and id.id.homografNr is None): # missing homografNr are caught below
                    yield DuplicateId(namespace=id.namespace, entry=ids[id].entry, entry2=e, id=id)

            else:
                ids[id] = source

            # Populate index by ortografi/homografNr
            if id.type == TEXT and source.visible:
                by_ortografi[id.namespace, id.id.ortografi].append(id)

    # Check for missing or unnecessary homografNr
    for (namespace, ortografi), homograf_ids in by_ortografi.items():
        def key(id):
            hnr = id.id.homografNr
            return -1 if hnr is None else hnr
        homograf_ids = sorted(homograf_ids, key=key)

        def homografer():
            return [ids[id] for id in homograf_ids]

        if len(homograf_ids) == 1 and homograf_ids[0].id.homografNr is not None: # unnecessary hnr
            yield HomografWrong(namespace, ortografi, homografer(), "onödigt homografnummer")
            continue

        if any(id.id.homografNr is None for id in homograf_ids):
            if len(homograf_ids) > 1: # missing hnr
                yield HomografWrong(namespace, ortografi, homografer(), "homografnummer saknas")

            homograf_ids = [id for id in homograf_ids if id.id.homografNr is not None]

        homograf_nrs = [id.id.homografNr for id in homograf_ids]
        if homograf_nrs != list(range(1, len(homograf_nrs)+1)): # wrong hnr
            yield HomografWrong(namespace, ortografi, homografer(), "icke-sekventiella homografnummer")

    return

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
