for entry in entry_queries.all_entries("salex", expand_plugins=False):
    entry = entry.entry

    ortografi = entry.get("ortografi")
    ordled = entry.get("saol", {}).get("ordled")

    replacements = {
        "·": "",
        "|": "",
        "bbb": "bb",
        "ttt": "tt",
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
            print(ortografi, ordled)
