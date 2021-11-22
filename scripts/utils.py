from datetime import datetime, date
import os
import pandas as pd
from tkinter.filedialog import askopenfile
import tkinter as tk


def load_config():
    # Load csv as dataframe and transform it to form a dictionary
    df_dict = pd.read_csv('.\\scripts\\resources\\config.csv', encoding='utf-8').set_index('key').T.to_dict('list')

    config_dict = {}
    for k in df_dict.keys():
        # get value from the list and assign correct type
        config_dict[k] = int(df_dict[k][0]) if df_dict[k][0].isnumeric() else str(df_dict[k][0])

    return config_dict

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


def text_insert(text_box, msg, left_newline=False, right_newline=False):
    import tkinter as tk
    output_msg = iif(left_newline, '\n', '') + msg + iif(right_newline, '\n', '')
    text_box.insert(tk.END, output_msg)


def iif(statement, true_part, false_part):
    return true_part if statement else false_part


def get_signature_and_isrevision(lng:str, filename):
    # Create new signature or recognize the current one from pattern
    if filename[:4] == 'REV_':
        print('Revision recognized')
        return filename, True
    else:
        saving_date = datetime.now().strftime('%m%d%Y%H%M%S')
        signature = 'REV_' + lng[:2] + saving_date
        print(f'Creating new signature: {signature}')
        return signature, False


def make_datetime(d):
    # transforms date-like string in database to datetime format
    return datetime(int(d[6:10]), int(d[:2]), int(d[3:5]), int(d[12:14]), int(d[15:17]), int(d[18:20]))


def make_date(d):
    # transforms date-like string in database to datetime format
    return date(int(d[6:10]), int(d[:2]), int(d[3:5]))


def make_todaytime():
    return datetime(datetime.now().year, datetime.now().month, datetime.now().day, datetime.now().hour, datetime.now().minute, datetime.now().second)


def make_todayte():
    return date(datetime.now().year, datetime.now().month, datetime.now().day)


def load_dataset(file_path=None):
    dataset = pd.DataFrame()

    if file_path is None:

        # Get File Path
        root = tk.Tk()
        root.withdraw()
        dataset_path = askopenfile(initialdir='.')
        if dataset_path != None:

            # Check if extension is supported
            extension = get_filename_from_path(dataset_path.name,True)[-3:]
            if extension != 'csv':
                print(f'Chosen extension is not supported: {extension}')
                return None, None

            dataset = pd.read_csv(dataset_path.name, encoding='utf-8')
            dataset = dataset.sample(frac=1).reset_index(drop=True)
            return dataset, dataset_path.name
        else:
            return None, None
        
    else: # FilePath provided
        dataset = pd.read_csv(file_path, encoding='utf-8')
        dataset = dataset.sample(frac=1).reset_index(drop=True)
        return dataset, file_path
    

def save(dataset:pd.DataFrame(), signature):
    config = load_config()

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