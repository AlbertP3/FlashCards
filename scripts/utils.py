from datetime import datetime, date
import os
from zipapp import get_interpreter
from numpy import isin
import pandas as pd
import re
import configparser
import csv
from PyQt5.QtCore import pyqtRemoveInputHook



def load_config():
    config = configparser.RawConfigParser(inline_comment_prefixes=None)
    config.read('./scripts/resources/config.ini')
    return config['DEFAULT']


config = load_config()


def update_config(key, new_value):
    old_config = configparser.RawConfigParser(inline_comment_prefixes=None)
    old_config.read('./scripts/resources/config.ini')
    old_config.set('DEFAULT', key, new_value)
    with open('./scripts/resources/config.ini', 'w') as configfile:
        old_config.write(configfile)

    
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
    # transforms date-like string from database to datetime format
    return datetime(int(d[6:10]), int(d[:2]), int(d[3:5]), int(d[12:14]), int(d[15:17]), int(d[18:20]))


def make_date(d):
    # transforms date-like string from database to datetime format
    return date(int(d[6:10]), int(d[:2]), int(d[3:5]))


def make_todaytime():
    return datetime(datetime.now().year, datetime.now().month, datetime.now().day, 
                    datetime.now().hour, datetime.now().minute, datetime.now().second)


def make_todayte():
    return date(datetime.now().year, datetime.now().month, datetime.now().day)


def save_revision(dataset:pd.DataFrame(), signature):
    try:
        file_name = signature
        dataset.to_csv(config['revs_path'] + file_name + '.csv', index=False)
        save_success = True
    except PermissionError:
        print('Permission Denied. Please close the file before modifications')
        save_success = False
    return save_success
     

def get_most_similar_file(path, lookup_file, if_nothing_found='load_any'):
    files = get_files_in_dir(path)
    for file in files:
        if re.match(lookup_file.lower(), file.lower()) is not None:
            return file
            
    if if_nothing_found == 'load_any':
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


def get_files_in_dir(path, include_extension = True, exclude_open=True):
    files_list = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
    if not include_extension:
        files_list = [f.split('.')[0] for f in files_list]
    if exclude_open:
        files_list[:] = [f for f in files_list if not f.startswith('~$')]
    return files_list


def format_timedelta(timedelta):
    if ',' in str(timedelta): # timedelta is more than 1 day
        time_value = str(timedelta.days)
        interval = 'Day'
    else:
        timedelta = str(timedelta).split(':')
        if timedelta[0] != '0':
            interval, id = 'Hour', 0
        elif timedelta[1] != '00':
            interval, id = 'Minute', 1
        else:
            interval, id = 'Second', 2
        time_value =  str(timedelta[id])

    if time_value.startswith('0'): 
        time_value = time_value[1:]

    suffix = 's' if time_value != '1' else ''
            
    return f'{time_value} {interval}{suffix}'


def get_signature(file_name, lng_gist, is_revision):
        # create unique signature for currently loaded rev
        # or return filename for lng
        if is_revision:
            signature = file_name
        else:
            # update_signature_timestamp() is directly dependent on this format
            saving_date = datetime.now().strftime('%m%d%Y%H%M%S')
            signature = 'REV_' + lng_gist + saving_date
        return signature


def update_signature_timestamp(signature):
    # Tighly coupled with get_signature
    updated_signature = signature[:6] + datetime.now().strftime('%m%d%Y%H%M%S')
    return updated_signature


def ask_user_for_custom_signature():
    # alternative: simpledialog.askstring('Saving File', 'Enter name for the file: ', initialvalue=signature)
    pyqtRemoveInputHook()
    custom_signature = input('Enter save prefix: ')
    return custom_signature


def get_lng_from_signature(signature):
    lngs = config['languages'].split('|')
    matched_lng = ''
    for lng in lngs:
        if lng in signature:
            matched_lng = lng
    return matched_lng


def load_dataset(file_path, do_shuffle=True):
    extension = get_filename_from_path(file_path, True).split('.')[-1]

    # Choose File Extension Handler
    try:
        if extension in ['csv', 'txt']:
            dataset = read_csv(file_path)
        elif extension in ['xlsx', 'xlsm']:  
            dataset = read_excel(file_path)
        else:
            print(f'Chosen extension is not (yet) supported: {extension}')
    except Exception as e:
        print(f'Unable to load requested {extension} file due to ' + str(e))
        dataset = pd.DataFrame()

    if do_shuffle:
        dataset = dataset.sample(frac=1).reset_index(drop=True)

    return dataset


def read_csv(file_path):
        dataset = pd.read_csv(file_path, encoding='utf-8',sep=get_dialect(file_path))   
        return dataset


def get_dialect(dataset_path):
    data = list()
    with open(dataset_path, 'r', encoding='utf-8') as csvfile:
        csvreader = csv.reader(csvfile)
        for r in csvreader:
            data.append(r)
    return csv.Sniffer().sniff(str(data[1]) + '\n' + str(data[2]), delimiters=';,').delimiter


def read_excel(file_path):
    if 'sht_pick' in config['optional'].split('|'):
       sht_id = get_sheet_id()
    else:
        sht_id = 0
    return pd.read_excel(file_path, sheet_name=sht_id)


def get_sheet_id():
     # input() causes infitnite loop of 'QCoreApplication already running printouts
    pyqtRemoveInputHook()
    sht_input = input('Input sheet name or index: ')
    return int(sht_input) if str(sht_input).isnumeric() else str(sht_input)


def dataset_is_valid(dataset:pd.DataFrame):
    rows_count = dataset.shape[0]
    cols_count = dataset.shape[1]
    if rows_count < 1:
        is_valid = False
    elif cols_count == 2:
        is_valid = True
    elif cols_count > 2:
        print(f'Selected file has {cols_count} columns. Only first 2 will be loaded')
        is_valid = True  # as dataset is still viable
    elif cols_count < 2:
        print('Selected file is invalid - not enough columns. Min is 2.')
        is_valid = False
    return is_valid


def validate_setup():

    # Database
    if config['db_path'].split('/')[-1] not in [f for f in os.listdir(config['resources_path'])]:
        print('Initializing new Database')
        pd.DataFrame(columns=['TIMESTAMP','SIGNATURE','TOTAL','POSITIVES']).to_csv(config['db_path'])

    # Lngs folder
    lngs_dir_name = config['lngs_path'].split('/')[-2]
    if lngs_dir_name not in [f for f in os.listdir('.')]:
        os.mkdir('./' + lngs_dir_name)

    # Revs folder
    revs_dir_name = config['revs_path'].split('/')[-2]
    if revs_dir_name not in [f for f in os.listdir('.')]:
        os.mkdir('./' + revs_dir_name)


def get_pretty_print(list_, extra_indent=1, separator=''):
    printout = '' 
    longest_elements = list()

    # convert to list
    if isinstance(list_, dict):
        list_ = [[k, v] for k, v in list_.items()]

    # preprocess separator
    if not isinstance(separator, list):
        separator = [separator for _ in range(len(list_[0]))]
    separator[-1] = ''


    for k in range(len(list_[0])):
        # find longest element for each sub-list
        longest_elements.append(max([len(str(item[k])) for item in list_]))

    for item in list_:
        line = ''
        for sub_index, sub_item in enumerate(item):
            indentation = get_indentation(longest_elements[sub_index], len(str(sub_item)), extra_indent, separator[sub_index])
            line+=f'{sub_item}{indentation}'
        # remove trailing indentation and append newline
        printout += line + '\n'
    
    return printout[:-2]


def get_indentation(max_len, sub_item_len, extra_indent, separator):
    indent_len = max_len - sub_item_len + 2*extra_indent

    # if max_len is even: allows putting separator in the middle
    if max_len % 2 == 0:
        indent_len+=1

    indent = [' ' for _ in range(indent_len)]
    indent[-extra_indent-1] = separator
    return ''.join(indent)