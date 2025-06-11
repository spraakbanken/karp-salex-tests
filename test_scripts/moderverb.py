from utils.salex import is_visible, EntryWarning, SAOL, Id, LNR, entry_cell
from tqdm import tqdm
from dataclasses import dataclass
from karp.lex.domain.dtos import EntryDto


@dataclass(frozen=True)
class InflectionClassMismatch(EntryWarning):
    moderverb: EntryDto

    def category(self):
        return "Ptv rxv böjningsklass (SAOL)"

    def to_dict(self):
        return super().to_dict(include_ordbok=False) | {
            "Böjningsklass": self.entry.entry.get("böjningsklass"),
            "Moderverb": entry_cell(self.moderverb, self.namespace),
            "Moderverb böjningsklass": self.moderverb.entry.get("böjningsklass"),
        }


def test_moderverb(entries, ids):
    for entry in tqdm(entries, desc="Checking moderverb"):
        if entry.entry.get("ingångstyp") not in ["partikelverb", "reflexivt_verb"]:
            continue
        böjningsklass = entry.entry.get("böjningsklass")
        for namespace in [SAOL]:
            body = entry.entry.get(namespace.path)
            if not body:
                continue
            if not is_visible("", body):
                continue

            moderverb_ref = Id(SAOL, LNR, body.get("moderverb"))
            moderverb_loc = ids.get(moderverb_ref)
            if not moderverb_loc:
                continue

            moderverb = moderverb_loc.entry
            moderverb_böjningsklass = moderverb.entry.get("böjningsklass")

            if böjningsklass != str(moderverb_böjningsklass):
                yield InflectionClassMismatch(entry, namespace, moderverb)
