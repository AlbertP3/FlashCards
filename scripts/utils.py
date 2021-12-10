from datetime import datetime, date
import os
import pandas as pd
import re



def load_config():
    # Load csv as dataframe and transform it to form a dictionary
    df_dict = pd.read_csv('.\\scripts\\resources\\config.csv', encoding='utf-8').set_index('key').T.to_dict('list')

    config_dict = {}
    for k in df_dict.keys():
        # get value from the list and assign correct type
        config_dict[k] = int(df_dict[k][0]) if df_dict[k][0].isnumeric() else str(df_dict[k][0])

    return config_dict

config = load_config()

def get_abs_path_from_caller(file_name, abs_path=None):
    from os import path
    from inspect import stack
    if abs_path is None:
        abs_path = path.abspath((stack()[1])[1])
        abs_path = path.join(path.dirname(abs_path), file_name)
    return abs_path


def get_relative_path_from_abs_path(abs_path):
    return '.\\' + os.path.relpath(abs_path)


def get_filename_from_path(path, include_extension=False):
    from ntpath import basename
    if include_extension:
        filename = basename(path)
    else:
        filename = (basename(path)).split('.')[0]
    return filename 


def get_sign(num, plus_sign='+', neg_sign='-'):
    if num > 0:
        return plus_sign
    elif num < 0:
        return neg_sign
    else:
        return ''


def make_datetime(d):
    # transforms date-like string in database to datetime format
    return datetime(int(d[6:10]), int(d[:2]), int(d[3:5]), int(d[12:14]), int(d[15:17]), int(d[18:20]))


def make_date(d):
    # transforms date-like string in database to datetime format
    return date(int(d[6:10]), int(d[:2]), int(d[3:5]))


def make_todaytime():
    return datetime(datetime.now().year, datetime.now().month, datetime.now().day, 
                    datetime.now().hour, datetime.now().minute, datetime.now().second)


def make_todayte():
    return date(datetime.now().year, datetime.now().month, datetime.now().day)


def save(dataset:pd.DataFrame(), signature):

    # Check if revision folder (name only) exists else create a new one
    if config['revs_path'][2:] not in [f for f in os.listdir('.')]: 
        os.mkdir(config['revs_path'][2:])

    # file_name = simpledialog.askstring('Saving File', 'Enter name for the file: ', initialvalue=signature)
    file_name = signature
    dataset.to_csv(config['revs_path'] + '\\' + file_name + '.csv', index=False)
    print('Saved Successfully')

     
def update_config(key, new_value):
    old_config = load_config()
    config = pd.read_csv(old_config['resources_path'] + '\\config.csv', encoding='utf-8')
    config.loc[config.key == key] = [key, new_value]
    config.to_csv(old_config['resources_path'] + '\\config.csv', index=False)


def get_most_similar_file(path, name, nothing_found=None):
    files = get_files_in_dir(path)
    for file in files:
        if re.match(name.lower(), file.lower()) is not None:
            return file
            
    if nothing_found == 'load_any':
        return files[0] 


def remove_layout(layout):
    # https://stackoverflow.com/questions/37564728/pyqt-how-to-remove-a-layout-from-a-layout
     if layout is not None:
         while layout.count():
             item = layout.takeAt(0)
             widget = item.widget()
             if widget is not None:
                 widget.setParent(None)
             else:
                 remove_layout(item.layout())


def get_files_in_dir(path):
    return [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]


def match_in_list_by_val(list_, val, ommit_extension=False):
    if ommit_extension is False:
        for i, v in enumerate(list_):
            if v == val:
                return i
    else:
        list_ = [str(i).split('.')[0] for i in list_]
        for i, v in enumerate(list_):
            if v == val:
                return i


def print_debug(msg):
    if config['debug'] == 'True':
        print(msg)