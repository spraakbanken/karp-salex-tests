from utils.salex import EntryWarning, SAOL, visible_part, entry_is_visible_in_printed_book
from dataclasses import dataclass
from tqdm import tqdm
import json
from karp.foundation.value_objects.unique_id import make_unique_id


@dataclass(frozen=True)
class VariantWarning(EntryWarning):
    variant: str

    def category(self):
        return "Variantformer"

    def to_dict(self):
        result = super().to_dict(include_ordbok=False)
        return {
            "Huvudlemma": result["Ord"],
            "Variantform": self.variant,
        }


def make_variant_form(entry, variant):
    body = entry.entry["saol"]
    huvudlemma_text = entry.entry["ortografi"].replace(" ", "_")
    huvudlemma_id = body["id"]

    result = {
        "id": str(make_unique_id()),
        "ingångstyp": "variant",
        "ortografi": variant["ortografi"],
        "ordklass": entry.entry["ordklass"],
        "sorteringsform": variant["ortografi"],
        "böjningsklass": variant["böjningsklass"],
        "saol": {
            "id": variant["id"],
            "visas": variant["visas"] and body["visas"],
            "endastDigitalt": variant.get("endastDigitalt", False) or body.get("endastDigitalt", False),
            "ordled": variant["ordled"],
            "huvudlemma": f"+{huvudlemma_text}(refid=lnr{huvudlemma_id})",
        },
    }

    for field in ["homografNr", "böjning"]:
        if field in variant:
            result["saol"][field] = variant[field]

    return result


def test_missing_variantformer(entries, ids, replacements_file=None):
    variant_ids = set()
    variant_orto_h = set()
    for entry in tqdm(entries, desc="Checking variant forms"):
        if saol_lemma := visible_part(entry.entry.get("saol"), test=entry_is_visible_in_printed_book):
            if entry.entry.get("ingångstyp") == "variant":
                variant_ids.add(saol_lemma["id"])
                variant_orto_h.add((entry.entry["ortografi"], saol_lemma.get("homografNr")))

    for entry in tqdm(entries, desc="Checking variant forms"):
        if saol_lemma := visible_part(entry.entry.get("saol"), test=entry_is_visible_in_printed_book):
            for variant in saol_lemma.get("variantformer", []):
                orto_hnr = (variant["ortografi"], variant.get("homografNr"))
                if variant["id"] not in variant_ids and orto_hnr not in variant_orto_h:
                    yield VariantWarning(entry, SAOL, variant["ortografi"])

                    if replacements_file:
                        replacements_file.write(json.dumps(make_variant_form(entry, variant)) + "\n")
