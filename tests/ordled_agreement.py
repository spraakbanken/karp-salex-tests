from utils.testing import fields, per_entry

@fields("ordled")
@per_entry
def test_ordled_agreement(entry):
    ortografi = entry.get("ortografi")
    ordled = entry.get("saol", {}).get("ordled")

    replacements = {
        "·": "",
        "|": "",
#            "bbb": "bb", # comment out these two so that we get some test failures
#            "ttt": "tt",
        "sss": "ss",
        "lll": "ll",
        "rrr": "rr",
        "fff": "ff",
        "ppp": "pp",
        "ddd": "dd",
        "ggg": "gg",
        "nnn": "nn",
        "mmm": "mm",
    }

    if ortografi and ordled:
        squashed_ordled = ordled

        for k, v in replacements.items():
            squashed_ordled = squashed_ordled.replace(k, v)

        if ortografi != squashed_ordled:
            yield {"ordled": ordled}
