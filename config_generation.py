import json
from os.path import join
import importlib

directory = input("What is Agent directory?: ")

query = importlib.import_module(directory + ".query")

filename = input("Config Filename (Optional, default is agent.config): ") or "agent.config"

with open(join(directory,'config.template'), 'r') as f:
    params = json.load(f)
try:
    with open(join(directory,'agent.config'), 'r') as f:
        config = json.load(f)
except:
    config = {}

if list(config.values()).count(None) != len(config.values()):
    text = input('Should the Existing Config File be Overwritten? (y/n): ') or "n"
    for i in range(0,3):
        if text == "n":
            overwrite = False
        elif text == "y":
            overwrite = True
        else:
            text = input('Input not recognized. Please use y or n: ') or "n"

params['TZonPoint'], params['TsetZonPoint'], params['equip'] = query.query_model('building_model.ttl')

for k, v in params.items():
    if (v is None) & (config.get(k) is None):
        text = input(f'Add parameter {k}:')
        continue
    if overwrite:
        text = input(f'Add parameter {k}:')
        continue
    if v:
        config[k] = v
        continue

print("Config File:")
print(json.dumps(config, indent = 4))
save = input("Save Config? (y/n): ") or "n"

if save == "n":
    print("Abandoning Process")
    quit()
if save == "y":
    with open(join(directory,filename), 'w') as f:
        f.write(json.dumps(config, indent = 4))
else:
    print("input not recognized")
print("Fin")