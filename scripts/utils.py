from datetime import datetime, date
import os
import pandas as pd
from tkinter.filedialog import askopenfile
import tkinter as tk
from PyQt5.QtCore import pyqtRemoveInputHook
import re
import csv



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
        filename = basename(path)[:-4]
    return filename 


def get_sign(num, plus_sign='+', neg_sign='-'):
    if num > 0:
        return plus_sign
    elif num < 0:
        return neg_sign
    else:
        return ''


def get_signature_and_isrevision(lng:str, filename):
    # Create new signature or recognize the current one from pattern
    filename = filename.split('.')[0]
    if filename.startswith('REV_'):
        print(f'Revision recognized: {filename}')
        return filename, True
    else:
        saving_date = datetime.now().strftime('%m%d%Y%H%M%S')
        signature = 'REV_' + lng[:2] + saving_date
        print(f'Language loaded: {filename}')
        return signature, False


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


def load_dataset(file_path=None):
    dataset = pd.DataFrame()

    # Get Path to the File - let user choose or take the given argument
    if file_path in [None, False]:
        # Get File Path
        root = tk.Tk()
        root.withdraw()
        dataset_path = askopenfile(initialdir='.')

        # In case user cancels the form
        if dataset_path is None: 
            return None, None
        else:
            dataset_path = dataset_path.name

    else: # file path provided
        dataset_path = file_path

    extension = get_filename_from_path(dataset_path, True).split('.')[-1]

    # Choose File Extension Handler
    if extension in ['csv', 'txt']:
        try:
            dataset = pd.read_csv(dataset_path, encoding='utf-8', sep=get_dialect(dataset_path))   
            # Check & Handle Errors
            if dataset.shape[1] > 2:
                print(f'Dataset has {dataset.shape[1]} cols. Expected 2')
            elif dataset.shape[1] < 2:
                # some csv might look like tttttt,"ttttt"
                data = [r[:-1].split(',"') for r in dataset.values.tolist()]
                dataset = pd.DataFrame(data=data[1:], columns=data[0])
                if dataset.shape[1] < 2:
                    print("It's screwed beyond any salvation")
                    return None, None
        except pd.errors.ParserError:
            print('Unable to load requested .csv file')
            return None, None

    elif extension in ['xlsx', 'xlsm']:
        
        if 'sht_pick' in config['experimental'].split('|'):
            # input() causes infitnite loop of 'QCoreApplication already running' printouts
            pyqtRemoveInputHook()
            sht_input = input('Input sheet name or index: ')
            sht_id = int(sht_input) if str(sht_input).isnumeric() else str(sht_input)
        else:
            sht_id = 0
        dataset = pd.read_excel(dataset_path, sheet_name=sht_id)

    else:
        
        print(f'Chosen extension is not (yet) supported: {extension}')
        return None, None

    dataset = dataset.sample(frac=1).reset_index(drop=True)
    return dataset, dataset_path
    

def get_dialect(dataset_path):
    data = list()
    with open(dataset_path, 'r', encoding='utf-8') as csvfile:
        csvreader = csv.reader(csvfile)
        for r in csvreader:
            data.append(r)
    return csv.Sniffer().sniff(str(data[1]) + '\n' + str(data[2]), delimiters=';,').delimiter


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
    files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
    for file in files:
        if re.match(name.lower(), file.lower()) is not None:
            return file
            
    if nothing_found == 'load_any':
        return files[0] 
