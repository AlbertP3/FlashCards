from os import sep
import pandas as pd
import tkinter as tk
from utils import *
from tkinter.filedialog import askopenfile
from tkinter import simpledialog
from datetime import datetime

def load_dataset(file_path=None):
    dataset = pd.DataFrame()

    if file_path is None:

        # Get File Path
        root = tk.Tk()
        root.withdraw()
        dataset_path = askopenfile()
        if dataset_path != None:
            dataset = pd.read_csv(dataset_path.name, encoding='utf-8')
            dataset = dataset.sample(frac=1).reset_index(drop=True)
            return dataset, dataset_path.name
        else:
            return None, None
        
    else:
        dataset = pd.read_csv(file_path, encoding='utf-8')
        dataset = dataset.sample(frac=1).reset_index(drop=True)
        return dataset, file_path
    
   


def save(dataset:pd.DataFrame()):
    saving_date = datetime.now().strftime('%m%d%Y%H%M%S')
    default_file_name = 'R' + dataset.columns.tolist()[0] + saving_date
    file_name = simpledialog.askstring('Saving File', 'Enter name for the file: ', initialvalue=default_file_name)
    dataset.to_csv(file_name + '.csv', index=False)





