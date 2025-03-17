from utils.salex import EntryWarning, entry_cell, VARIANT_LNR, LNR
from dataclasses import dataclass
from tqdm import tqdm

# TODO test variant forms
# TODO check that no homografNr

@dataclass(frozen=True)
class VariantWarning(EntryWarning):
    other: IdLocation | None
    comment: str

    def category(self):
        return "Variantformer"

    def to_dict(self):
        result = super().to_dict()
        if self.other is not None:
            result["Ord 2"] = self.other
        if self.comment is not None:
            result["Info"] = self.comment
        return result

def test_variantformer(entries, ids):
    for id, entry in tqdm(ids.items(), desc="Checking variant forms"):
        if id.type == VARIANT_LNR:
            target_id = id.replace(type=LNR)

            if target_id not in ids:
                yield VariantWarning(entry, SAOL, None,
                continue

    for entry in tqdm(entries, desc="Checking variant forms"):
        if saol_lemma := entry.entry.get("saol"):
            if saol_lemma.get("ingångstyp") == "variant":
                variants_by_id[saol_lemma["id"]] = entry

            for variant_form in saol_lemma.get("variantformer", []):
                sub_variants_by_id[variant_form["id"]] = (entry, variant_form)

    for id, variant in variants_by_id.items():
        if id not in sub_variants_by_id:
            yield VariantWarning(entry, SAOL, None,
