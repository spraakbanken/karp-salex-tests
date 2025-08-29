import pickle
import re


def guess_keys(data, path=[]):
    if isinstance(data, list):
        for x in data:
            yield from guess_keys(x, path)

    if isinstance(data, str):
        if re.match(".*xnr[0-9].*", data) or "refid" in data:
            yield ("ref", path)

    if isinstance(data, dict):
        for field, value in data.items():
            if field == "x_nr":
                yield (field, path + [field])
            elif field.endswith("id") or field.endswith("nr") or field.endswith("hänvisning"):
                yield ("id", path + [field])

            yield from guess_keys(value, path + [field])


def guess_keys_entries(entries):
    for entry in entries:
        for kind, path in guess_keys(entry.entry):
            yield kind, ".".join(path)


with open("entries.pickle", "rb") as file:
    entries = pickle.load(file)

for kind, path in set(guess_keys_entries(entries)):
    print(path, kind)

exit()
