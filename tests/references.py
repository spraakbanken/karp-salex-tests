from karp.foundation import json
from collections import defaultdict
from utils.salex import find_ids, find_refs, entry_name, is_visible, SO, SAOL, Id, IdLocation, parse_ref, TEXT, TextId, variant_fields, EntryWarning, entry_cell, no_refid_fields, id_fields
from utils.testing import highlight, rich_string_cell
from dataclasses import dataclass
from tqdm import tqdm
import re
from karp.lex.domain.dtos import EntryDto

refid_re = re.compile(r"\+([^ +]*)\(refid=([a-zA-Z0-9]*)\)(?!\(refid=)")
id_re = re.compile(r"(?:x|l|kc)nr[a-zA-Z0-9]+")
only_refid_re = re.compile(r"refid")
plus_re = re.compile(r"\+(?![0-9])(?!verb)\w+")

def match_contains(m1, m2):
    return m1.start() <= m2.start() and m1.end() >= m2.end()

@dataclass(frozen=True)
class DuplicateId(Warning):
    entry: EntryDto
    entry2: EntryDto
    id: Id

    def category(self):
        return f"Duplicate id ({self.id.namespace})"

    def to_dict(self):
        return {
            "Ord": entry_cell(self.entry, self.id.namespace),
            "Ord 2": entry_cell(self.entry2, self.id.namespace),
            "Id": self.id
        }

@dataclass(frozen=True)
class HomografWrong(Warning):
    namespace: str
    ortografi: str
    homografer: list[IdLocation]
    message: str

    def category(self):
        return f"Homografnummer ({self.namespace})"

    def to_dict(self):
        result = {"Ord": self.ortografi, "Fel": self.message}
        for i, homograf in enumerate(self.homografer, start=1):
            result[f"Homograf {i}"] = homograf
        return result

@dataclass(frozen=True)
class BadReference(Warning):
    location: IdLocation
    reference: Id
    target: IdLocation | None
    comment: str | None = None

    def category(self):
        # Ignore TEXT references for now
        if self.reference.type == TEXT:
            return

        if self.target is not None:
            if self.target.visible:
                result = f"Kanske felpekande ({self.reference.namespace})"
            else:
                result = f"Hänvisningar till förråd ({self.reference.namespace})"
        else:
            result = f"Okända hänvisningar ({self.reference.namespace})"

        return result

    def to_dict(self):
        result = {
            "Ord": self.location,
            "Fält": json.path_str(self.location.path, strip_positions=True),
        }
        if self.target is not None and self.target.visible:
            result["Hänvisning"] = self.location.text
        else:
            result["Hänvisning"] = self.reference
        if self.target is not None:
            result["Hänvisar till"] = self.target
        if self.comment is not None:
            result["Kommentar"] = self.comment
        return result

@dataclass(frozen=True)
class BadReferenceSyntax(Warning):
    location: IdLocation
    text: str

    def category(self):
        return f"Okända hänvisningar ({self.location.namespace})"

    def to_dict(self):
        result = {
            "Ord": self.location,
            "Fält": json.path_str(self.location.path, strip_positions=True),
            "Hänvisning": rich_string_cell(*highlight(self.text, self.location.text))
        }
        return result

def test_references(entries, inflection):
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

    for entry in tqdm(entries, desc="Checking references"):
        for ref, loc in find_refs(entry):
            if not loc.visible: continue

            if ref not in ids or not ids[ref].visible:
                if ref not in ids and ref.type == TEXT and ref.id.homografNr is None and (ref.namespace, ref.id.ortografi) in by_ortografi:
                    comment = "homografnummer saknas?"
                else:
                    comment = None
                yield BadReference(loc, ref, ids.get(ref), comment)

        # Check +hund(refid=lnr123456)-style references
        for namespace in [SO, SAOL]:
            body = entry.entry.get(namespace.path, {})
            for path in json.all_paths(body):
                if not is_visible(path, body): continue
                path_str = json.path_str(path, strip_positions=True)
                if path_str in no_refid_fields[namespace]: continue
                if path_str in id_fields[namespace]: continue
                value = json.get_path(path, body)
                if not isinstance(value, str): continue

                references = list(refid_re.finditer(value))

                # Check for references with bad syntax
                tests = [plus_re, only_refid_re]
                if "hänvisning" not in path: tests.append(id_re)

                loc = IdLocation(entry, namespace, path, value)
                errors = []
                for regexp in tests:
                    for maybe_ref in regexp.finditer(value):
                        if not any(match_contains(ref, maybe_ref) for ref in references):
                            errors.append(BadReferenceSyntax(loc, maybe_ref.group(0)))

                # Only generate one error per string, since bad references tend
                # to trigger more than one of the regexp tests
                yield from errors[:1]

                # Check that target of reference is correct
                for ref in references:
                    loc = IdLocation(entry, namespace, path, ref.group(0))
                    word = ref.group(1).replace("_", " ").replace("(", "").replace(")", "")
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
                    if word not in [form for w in [target_word, *variant_forms] for form in inflection.inflected_forms(target_entry, w)]:
                        # TODO: report mistakenly pointing at variant
                        # form as a minor error?
                        yield BadReference(loc, id, ids.get(id), f"pekar inte på {word}")
