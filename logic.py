from os import sep
import pandas as pd

def load_dataset():
    # Get File Path
    import tkinter as tk
    from tkinter.filedialog import askopenfile
    root = tk.Tk()
    root.withdraw()
    dataset_path = askopenfile()
    if dataset_path != None:
        dataset = pd.read_csv(dataset_path.name, encoding='utf-8')
        dataset = dataset.sample(frac=1).reset_index(drop=True)
        return dataset, True
    else:
        return None, False


def save():
    pass






