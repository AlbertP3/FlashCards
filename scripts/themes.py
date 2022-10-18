from utils import Config
import os
import configparser

config = Config()


def load_themes() -> dict:
    themes_dict = dict()
    themes_path =  os.path.join(config['resources_path'], 'themes')
    theme_files = [f for f in os.listdir(themes_path) if f.endswith('.ini')]
    parser = configparser.RawConfigParser(inline_comment_prefixes=None)

    for file in theme_files:
        parser.read(os.path.join(themes_path, file))
        theme_name = file.split('.')[0]
        themes_dict[theme_name] = dict(parser.items('THEME'))

    return themes_dict
    
