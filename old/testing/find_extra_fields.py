from karp.foundation import json
from collections import Counter
import pickle
from tqdm import tqdm


def path_shown(entry, path):
    for i in range(len(path)):
        superpath = path[:i]
        visas = superpath + ["visas"]
        if json.has_path(visas, entry.entry) and not json.get_path(visas, entry.entry):
            return False
    return True


def shown(entry, field):
    return any(path_shown(entry, path) for path in json.expand_path(field, entry.entry))


def resource_fields(resource_id):
    for entry in tqdm(entry_queries.all_entries(resource_id, expand_plugins=False)):
        #    for entry in pickle.load(open("../lint/old-entries.pickle", "rb")):
        for field in json.all_fields(entry.entry):
            if shown(entry, field):
                yield field


def resource_config_fields(resource_id):
    resource = resource_queries.by_resource_id(resource_id)
    yield from resource.config.nested_fields()


salex_data_fields = Counter(resource_fields("salex"))
for field in resource_config_fields("salex"):
    del salex_data_fields[field]

for field in sorted(salex_data_fields):
    print(field, salex_data_fields[field])

exit()
