from datetime import datetime
import PyQt5.QtWidgets as widget
from PyQt5 import QtGui
from PyQt5.QtCore import pyqtRemoveInputHook
from utils import *
import pandas as pd
import csv



def load_dataset(file_path):
    dataset = pd.DataFrame()

    extension = get_filename_from_path(file_path, True).split('.')[-1]

    # Choose File Extension Handler
    if extension in ['csv', 'txt']:
        try:
            dataset = load_csv(file_path)
        except pd.errors.ParserError:
            print('Unable to load requested .csv file')
            return None, None
    elif extension in ['xlsx', 'xlsm']:  
        dataset = read_excel(file_path)
    else:
        print(f'Chosen extension is not (yet) supported: {extension}')
        return None

    dataset = dataset.sample(frac=1).reset_index(drop=True)
    return dataset


def get_dialect(dataset_path):
    data = list()
    with open(dataset_path, 'r', encoding='utf-8') as csvfile:
        csvreader = csv.reader(csvfile)
        for r in csvreader:
            data.append(r)
    return csv.Sniffer().sniff(str(data[1]) + '\n' + str(data[2]), delimiters=';,').delimiter


def load_csv(file_path):
    dataset = pd.read_csv(file_path, encoding='utf-8', sep=get_dialect(file_path))   
    if dataset.shape[1] < 2:  # Check & Handle Errors
        print_debug('Resorting to backup csv loading plan. Expected sep= ttt,"tttt"')
        data = [r[:-1].split(',"') for r in dataset.values.tolist()]
        dataset = pd.DataFrame(data=data[1:], columns=data[0])
    return dataset


def read_excel(file_path):
    if 'sht_pick' in config['experimental'].split('|'):
        # input() causes infitnite loop of 'QCoreApplication already running' printouts
        pyqtRemoveInputHook()
        sht_input = input('Input sheet name or index: ')
        sht_id = int(sht_input) if str(sht_input).isnumeric() else str(sht_input)
    else:
        sht_id = 0
    return pd.read_excel(file_path, sheet_name=sht_id)


def dataset_is_valid(dataset):
    if type(dataset) == pd.DataFrame:
        cols_count = dataset.shape[1]
        if cols_count == 2:
            return True
        elif cols_count > 2:
            print(f'Selected file has {cols_count} columns. Expected 2')
            return True  # as dataset is still viable
        else:
            print('Selected file is invalid - not enough columns. Min is 2.')
            return False
    else:
        print('Selected file is screwed beyond salvation.')
        return False



class Load_dialog(widget.QWidget):
    
    def __init__(self, main_window):
        self.main_window = main_window
        super(Load_dialog, self).__init__(None)
        self.selected_file_name = None
    

    def get_load_layout(self):
        self.config = load_config()
        self.arrange_window()
        return self.load_layout


    def arrange_window(self):

        # Window Parameters
        self.buttons_height = 45
        self.textbox_width = 250

        # Style
        self.textbox_stylesheet = (self.config['textbox_style_sheet'])
        self.button_style_sheet = self.config['button_style_sheet']
        self.font = self.config['font']
        self.font_button_size = self.config['efc_button_font_size']
        self.button_font = QtGui.QFont(self.font, self.font_button_size)

        # Elements
        self.load_layout = widget.QGridLayout()
        self.load_layout.addWidget(self.get_flashcard_files_list(), 0, 0)
        self.load_layout.addWidget(self.create_load_button(), 1, 0)


    def create_load_button(self):
        self.load_button = widget.QPushButton(self)
        self.load_button.setFixedHeight(self.buttons_height)
        self.load_button.setFixedWidth(self.textbox_width)
        self.load_button.setFont(self.button_font)
        self.load_button.setText('Load')
        self.load_button.setStyleSheet(self.button_style_sheet)
        self.load_button.clicked.connect(self.load_selected)
        return self.load_button
    

    def get_flashcard_files_list(self):
        self.flashcard_files_qlist = widget.QListWidget(self)
        self.flashcard_files_qlist.setFont(self.button_font)
        self.flashcard_files_qlist.setStyleSheet(self.textbox_stylesheet)
        self.flashcard_files_qlist.setFixedWidth(self.textbox_width)
        [self.flashcard_files_qlist.addItem(str(file).split('.')[0]) for file in self.get_lng_files() if str(file)[:2] != '~$']
        [self.flashcard_files_qlist.addItem(str(file).split('.')[0]) for file in self.get_rev_files() if str(file)[:2] != '~$']
        return self.flashcard_files_qlist


    def get_lng_files(self):
        self.lng_files_list = get_files_in_dir(self.config['lngs_path'])
        self.lng_files_list.sort(key=lambda e: e[6:14], reverse=True)  
        return self.lng_files_list


    def get_rev_files(self):
        self.rev_files_list = get_files_in_dir(self.config['revs_path'])
        self.rev_files_list.sort(key=lambda e: e[6:14], reverse=True    )  
        return self.rev_files_list


    def load_selected(self):

        selected_li = self.flashcard_files_qlist.currentItem().text()

        # Deterime if selected file is rev or lng by its position in the list
        concatenated_lists = self.lng_files_list + self.rev_files_list
        sel_item_index = match_in_list_by_val(concatenated_lists, selected_li, True)

        if sel_item_index < len(self.lng_files_list):
            self.get_params(self.lng_files_list, selected_li, self.config['lngs_path'])
            self.is_revision = False
        else:
            self.get_params(self.rev_files_list, selected_li, self.config['revs_path'])
            self.is_revision = True

        self.update_main_window_params(onload_file_path=self.file_path)


    def get_params(self, lookup_list, selected_li, path):
        selected_rev_id = match_in_list_by_val(lookup_list, selected_li, ommit_extension=True)
        selected_rev = lookup_list[selected_rev_id]
        self.file_path = f"{path}/" + str(selected_rev)
        self.data = load_dataset(self.file_path)
        self.selected_file_name = str(selected_rev).split('.')[0]


    def load_file(self, file_path, revs_path):
        self.data = load_dataset(file_path)
        file_path_parts = file_path.split('/')
        self.selected_file_name = file_path_parts[-1].split('.')[0]
        # Determine is_revision based on directory
        self.is_revision = True if file_path_parts[-2] == revs_path[2:] else False
        self.update_main_window_params(onload_file_path=file_path)


    def update_main_window_params(self, onload_file_path=None):
        if dataset_is_valid(self.data):
            self.main_window.set_dataset(self.data)
            self.main_window.set_signature(self.get_signature())
            self.main_window.set_is_revision(self.is_revision)
            self.main_window.set_title(self.signature if self.is_revision else self.selected_file_name)
            self.main_window.del_side_window()
            self.main_window.reset_flashcard_parameters()
            if onload_file_path is not None:
                update_config('onload_file_path', onload_file_path)

    
    def get_signature(self):
        if self.is_revision:
            print(f'Revision recognized: {self.selected_file_name}')
            self.signature = self.selected_file_name
        else:
            saving_date = datetime.now().strftime('%m%d%Y%H%M%S')
            self.signature = 'REV_' + str(self.data.columns.tolist()[0])[:2] + saving_date
            print(f'Language loaded: {self.selected_file_name}')
        return self.signature

