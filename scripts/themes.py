from utils import Config
import os
import json

config = Config()


def load_themes() -> dict:
    themes_dict = dict()
    themes_path =  os.path.join(config['resources_path'], 'themes')
    theme_files = [f for f in os.listdir(themes_path) if f.endswith('.json')]

    for f in theme_files:
        theme = json.load(open(os.path.join(themes_path, f), 'r'))
        theme_name = f.split('.')[0]
        themes_dict[theme_name] = theme

    return themes_dict
