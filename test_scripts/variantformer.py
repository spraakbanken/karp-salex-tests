from utils.salex import EntryWarning, entry_cell, Id, SAOL, LNR, IdLocation, parse_ref, visible_part
from dataclasses import dataclass
from tqdm import tqdm
from karp.foundation import json

# TODO test variant forms
# TODO check that no homografNr

@dataclass(frozen=True)
class VariantWarning(EntryWarning):
    other: IdLocation | None
    comment: str | None

    def category(self):
        return "Variantformer"

    def to_dict(self):
        result = super().to_dict(include_ordbok=False)
        return {
            "Variantlemma": result["Ord"],
            "Huvudlemma": self.other,
            "Info": self.comment,
        }

def test_variantformer(entries, ids):
    for entry in tqdm(entries, desc="Checking variant forms"):
        if saol_lemma := visible_part(entry.entry.get("saol")):
            if not saol_lemma["visas"]: continue
            if entry.entry.get("ingångstyp") == "variant":
                if saol_lemma.get("huvudbetydelser"):
                    yield VariantWarning(entry, SAOL, None, "variantlemmat har huvudbetydelse")

                if not "huvudlemma" in saol_lemma:
                    yield VariantWarning(entry, SAOL, None, "huvudlemma-fältet är tomt")
                    continue

                try:
                    target, _ = parse_ref(entry.entry, SAOL, "huvudlemma")
                except:
                    yield VariantWarning(entry, SAOL, None, "parse " + saol_lemma.get("huvudlemma", ""))
                    continue

                if target not in ids:
                    yield VariantWarning(entry, SAOL, None, "missing")
                    continue

                variant_parent = ids[target].entry.entry
                candidate_variants = [v for v in variant_parent["saol"].get("variantformer", []) if v["ortografi"] == entry.entry["ortografi"]]
                if len(candidate_variants) == 0:
                    yield VariantWarning(entry, SAOL, None, "huvudlemmat har inga matchande variantformer")
                elif len(candidate_variants) > 1:
                    yield VariantWarning(entry, SAOL, None, "huvudlemmat har flera matchande variantformer")
                else:
                    variant = candidate_variants[0]

                should_match = [
                    ("ordklass", variant_parent, "ordklass"),
                    ("ortografi", variant, "ortografi"),
                    #("böjningsklass", variant, "böjningsklass"),
                    ("saol.homografNr", variant, "homografNr"),
                    ("saol.ordled", variant, "ordled")
                ]

                for path1, other, path2 in should_match:
                    value1 = json.get_path(path1, entry.entry) if json.has_path(path1, entry.entry) else None
                    value2 = json.get_path(path2, other) if json.has_path(path2, other) else None

                    if value1 != value2:
                        yield VariantWarning(entry, SAOL, ids[target], f"olika {path2}: {value1}, {value2}")
