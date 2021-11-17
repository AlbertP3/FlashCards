import pandas as pd
import tkinter as tk
from utils import *
from tkinter.filedialog import askopenfile
from tkinter import simpledialog
import os


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
        
    else:
        dataset = pd.read_csv(file_path, encoding='utf-8')
        dataset = dataset.sample(frac=1).reset_index(drop=True)
        return dataset, file_path
    
   
def save(dataset:pd.DataFrame(), signature):
    # Check if revision folder exists else create a new one
    if 'revisions' not in [f for f in os.listdir('.')]: 
        os.mkdir(r'.\\revisions')

    # file_name = simpledialog.askstring('Saving File', 'Enter name for the file: ', initialvalue=signature)
    file_name = signature
    dataset.to_csv(r'.\\revisions\\' + file_name + '.csv', index=False)
    print('Saved Successfully')


def load_config():
    # Load csv as dataframe and transform it to form a dictionary
    df_dict = pd.read_csv('config.csv', encoding='utf-8').set_index('key').T.to_dict('list')

    config_dict = {}
    for k in df_dict.keys():
        # get value from the list and assign correct type
        config_dict[k] = int(df_dict[k][0]) if df_dict[k][0].isnumeric() else str(df_dict[k][0])

    return config_dict
    
     


