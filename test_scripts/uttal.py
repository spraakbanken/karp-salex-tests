from utils.salex import SAOL, SO, is_visible, EntryWarning
from utils.testing import markup_cell
from dataclasses import dataclass
from karp.foundation import json
from nltk.corpus import wordnet
from tqdm import tqdm
import re
from pathlib import Path

data_dir = Path(__file__).parent.parent / "data"

foreign_words = set()
for path in [data_dir / "english", data_dir / "french"]:
    with open(path, "r") as file:
        for line in file.readlines():
            line = line.strip()
            foreign_words.add(line.lower())


@dataclass(frozen=True)
class UttalWarning(EntryWarning):
    ortografi: str | None
    uttal: str

    def category(self):
        return f"Uttal ({self.namespace})"

    def to_dict(self):
        return super().to_dict() | {"Variantform": self.ortografi, "Uttal": markup_cell(self.uttal)}


# TODO keep track of how commonly each one is used, find the least common ones
pronunciations = [
    # vowels
    ("a", "ej"),
    ("a", "ä"),
    ("a", "å"),
    ("a", "e"),
    ("ai", "ä"),
    ("aigh", "ej"),
    ("e", "ä"),
    ("ea", "i"),
    ("ee", "i"),
    ("ei", "aj"),
    ("ei", "ej"),
    ("ei", "ä"),
    ("en", "aŋ"),
    ("er", "ör"),
    ("i", "aj"),
    ("i", "j"),
    ("i", "ä"),
    ("io", "ie"),
    ("o", "å"),
    ("o", "ö"),
    ("ou", "ao"),
    ("ow", "a"),
    ("u", "o"),
    ("u", "a"),
    ("è", "ä"),
    ("é", "e"),
    ("ig", "aj"),
    ("oi", "åj"),
    ("ä", "e"),
    ("ü", "y"),
    ("u", "v"),
    ("u", "f"),
    ("u", "y"),
    ("y", "ö"),
    # sk/sc/sh
    ("jou", "ʃo"),
    ("sc", "ʃ"),
    ("sch", "ʃ"),
    ("sh", "ʃ"),
    ("si", "ʃ"),
    ("sj", "ʃ"),
    ("sk", "ʃ"),
    ("ssi", "ʃ"),
    ("ti", "si"),
    ("ti", "tsi"),
    ("ti", "tʃ"),
    ("ti", "ʃ"),
    ("tj", "ç"),
    ("tj", "tç"),
    ("stg", "ʃ"),
    ("s", "ʃ"),  # German
    # c/k/x/z
    ("c", "k"),
    ("c", "s"),
    ("c", "tç"),
    ("c", "ç"),
    ("cc", "ks"),
    ("cc", "k"),
    ("cc", "s"),
    ("ch", "k"),
    ("ch", "tç"),
    ("ch", "ç"),
    ("ch", "ʃ"),
    ("ck", "k"),
    ("k", "ç"),
    ("k", "ʃ"),
    ("x", "ks"),
    ("z", "s"),
    ("ç", "s"),
    ("zz", "ts"),
    ("z", "ts"),
    # g/n/j
    ("g", "j"),
    ("gi", "dj"),
    ("g", "ʃ"),
    ("g", "j"),
    ("gi", "ʃ"),
    ("gn", "nj"),
    ("gn", "ŋn"),
    ("j", "ʃ"),
    ("j", "dj"),
    ("n", "ŋ"),
    ("ng", "ŋ"),
    ("nk", "ŋ"),
    # silent letters
    ("dg", "g"),
    ("ds", "s"),
    ("ts", "s"),
    ("dsk", "sk"),
    ("dzj", "dj"),
    ("e", ""),
    ("hr", "r"),
    ("mnd", "md"),
    ("rld", "rd"),
    ("dj", "j"),
    ("kh", "k"),
    ("ttd", "t"),
    # devoicing
    ("ds", "ts"),
    ("gs", "ks"),
    ("gt", "kt"),
    ("vs", "fs"),
    ("bs", "ps"),
    ("g", "k"),  # vigsel
    ("b", "p"),  # liebhaber
    # misc
    ("byte", "bajt"),
    ("eu", "ev"),
    ("eu", "ef"),
    ("euro", "jorå"),  # euro
    ("ice", "is"),  # service
    ("ligio", "lio"),  # religion
    ("qu", "kv"),  # quisling
    ("sci", "saj"),
    ("sci", "si"),  # scientologist
    ("sce", "se"),  # adolescens
    ("w", "v"),
    ("wh", "v"),  # whisky
    ("wh", "w"),  # whisky
    ("white", "oajt"),
    ("worce", "oo"),
    ("oo", "å"),
    ("qu", "kw"),  # SO
    ("qu", "ko"),  # SAOL
    ("y", "j"),  # yoga
    ("w", "o"),  # work
    ("ou", "o"),  # roulett
    ("oa", "åo"),  # roadie
    ("ill", "j"),  # ravaillac
    ("qu", "kv"),  # quizza
    ("zz", "s"),
    ("ñ", "nj"),
    ("ig", "ej"),  # mig/dig/sig
    ("god", "go"),
    ("v", "f"),  # German
    ("or", "ö"),  # work
    ("or", "å"),  # vorsteh
    ("3", "tre"),
    ("4", "fyra"),
    ("5", "fem"),
    ("ph", "f"),
    ("rg", "r"),  # morgon
    ("ou", "ao"),  # mountain
    ("ch", "χ"),  # German
    ("g", "j"),
    ("ei", "aj"),  # German
    ("ch", "ç"),  # German
    ("tjugo", "çuge"),
    ("tjugo", "çu"),
    ("th", "t"),
    ("ay", "ej"),
    ("fyrtio", "fört"),
    ("fyrtio", "förti"),
    ("fyrtio", "förtio"),
    ("med", "me"),
    ("oa", "o"),
    ("oa", "å"),
    ("qu", "k"),
    ("que", "k"),
    ("q", "k"),
    ("q", "ç"),
    ("gh", "g"),
    ("y", "aj"),
    ("une", "jon"),
    ("eu", "öj"),
    ("eu", "åj"),
    ("ss", "s"),
    ("psa", "sa"),
    ("ai", "aji"),
    ("nt", "ŋ"),
    ("ayr", "är"),
    ("shire", "ʃör"),
    ("as", "a"),
    ("beauty", "bjoti"),
    ("ähig", "äig"),
    ("nc", "ŋ"),
    ("n", "ŋ"),
    ("oa", "å"),
    ("ui", "i"),
    ("mot", "må"),
    ("ff", "f"),
    ("sverige", "sverje"),
    ("och", "å"),
    ("femtio", "femtio"),
    (":", ""),
    (" ", ""),
    # single letters
    ("b", "be"),
    ("c", "se"),
    ("d", "de"),
    ("f", "ef"),
    ("g", "ge"),
    ("h", "hå"),
    ("j", "ji"),
    ("k", "kå"),
    ("l", "el"),
    ("m", "em"),
    ("n", "en"),
    ("p", "pe"),
    ("q", "ku"),
    ("r", "är"),
    ("s", "es"),
    ("t", "te"),
    ("v", "ve"),
    ("w", "ve"),
    ("x", "eks"),
    ("z", "säta"),
]


def make_replacement(ortografi, uttal):
    if ortografi and uttal and ortografi[0] == uttal[0]:
        yield ortografi[1:], uttal[1:]

    if ortografi and uttal and ortografi[0:2] == uttal[0] + uttal[0]:  # doubled letters
        yield ortografi[2:], uttal[1:]

    for source, target in pronunciations:
        if ortografi.startswith(source) and uttal.startswith(target):
            yield ortografi[len(source) :], uttal[len(target) :]


def agrees1(ortografi, uttal):
    if ortografi == uttal:
        return True

    else:
        return any(agrees1(new_ortografi, new_uttal) for new_ortografi, new_uttal in make_replacement(ortografi, uttal))


def agrees(ortografi, uttal):
    if ortografi[0].isupper():
        return True

    deletions = {"´", "´", "[sup ", "]", "(", ")", "`"}
    for x in deletions:
        uttal = uttal.replace(x, "")

    # TODO is this something that should be fixed in SO?
    # First one is INTEGRAL (8747), second is LATIN SMALL LETTER ESH (643)
    uttal = uttal.replace("∫", "ʃ")

    if uttal.startswith("-"):
        return any(agrees(ortografi[i:], uttal[1:]) for i in range(1, len(ortografi)))

    elif uttal.endswith("-"):
        return any(agrees(ortografi[:i], uttal[:-1]) for i in range(1, len(ortografi)))

    else:
        return agrees1(ortografi, uttal)


def agrees_multiword(ortografi, uttal):
    ortografi = ortografi.split()

    for i in range(len(ortografi)):
        for j in reversed(range(i + 1, len(ortografi) + 1)):
            if agrees(" ".join(ortografi[i:j]), uttal):
                return True

    return False


def foreign(w):
    return w in foreign_words or wordnet.synsets(w, lang="eng") or wordnet.synsets(w, lang="fra")


def check_all_uttal(entry, namespace, ortografi_field, uttal_field, variant):
    body = entry.entry.get(namespace.path, {})

    delim = re.compile(r"[ -]")

    for ortografi_path in json.expand_path(ortografi_field, body):
        if not is_visible(ortografi_path, body):
            continue
        ortografi = json.get_path(ortografi_path, body)

        if not ortografi:
            print(namespace, ortografi_field, namespace)
            continue

        for uttal_path in json.expand_path(json.localise_path(uttal_field, ortografi_path), body):
            if not is_visible(uttal_path, body):
                continue
            uttals = json.get_path(uttal_path, body)

            typ_path = uttal_path[:-1] + ["typ"]
            if json.has_path(typ_path, body) and json.get_path(typ_path, body) in ["best. form", "plural"]:
                continue

            for uttal in uttals.split(","):
                uttal = uttal.strip()
                while uttal.endswith(";"):
                    uttal = uttal[:-1]
                if not uttal:
                    continue
                if not agrees_multiword(ortografi, uttal):
                    if foreign(ortografi) or all(foreign(w) for w in delim.split(ortografi)):
                        continue
                    yield UttalWarning(entry, namespace, ortografi if variant else None, uttal)


def test_uttal(entries):
    for entry in tqdm(entries, desc="Checking pronunciation"):
        # hack
        ortografi = entry.entry.get("ortografi")
        entry.entry.get("so", {})["ortografi"] = ortografi
        entry.entry.get("saol", {})["ortografi"] = ortografi
        yield from check_all_uttal(entry, SO, "ortografi", "uttal.fonetikparentes", False)
        yield from check_all_uttal(entry, SO, "variantformer.ortografi", "variantformer.uttal.fonetikparentes", True)
        yield from check_all_uttal(entry, SAOL, "ortografi", "uttal.form", False)
        yield from check_all_uttal(entry, SAOL, "variantformer.ortografi", "variantformer.uttal", True)
