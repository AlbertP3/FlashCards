import PyQt5.QtWidgets as widget
from PyQt5 import QtGui
from utils import *
import db_api


class Load_dialog(widget.QWidget):
    # Displays side window with list of all available files
    
    def __init__(self, main_window):
        self.main_window = main_window
        super(Load_dialog, self).__init__(None)
        self.selected_file_name = None
        self.config = load_config()
    

    def get_load_layout(self):
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
        self.font_button_size = int(self.config['efc_button_font_size'])
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
        self.load_button.clicked.connect(self.deploy_selected_flashcards_to_load_handler)
        return self.load_button
    

    def get_flashcard_files_list(self):
        self.flashcard_files_qlist = widget.QListWidget(self)
        self.flashcard_files_qlist.setFont(self.button_font)
        self.flashcard_files_qlist.setStyleSheet(self.textbox_stylesheet)
        self.flashcard_files_qlist.setFixedWidth(self.textbox_width)
        [self.flashcard_files_qlist.addItem(str(file).split('.')[0]) for file in self.get_lng_files()]
        [self.flashcard_files_qlist.addItem(str(file).split('.')[0]) for file in self.get_rev_files()]
        return self.flashcard_files_qlist


    def get_lng_files(self):
        self.lng_files_list = get_files_in_dir(self.config['lngs_path'])
        self.lng_files_list.sort(reverse=False)  
        return self.lng_files_list


    def get_rev_files(self):
        self.rev_files_list = get_files_in_dir(self.config['revs_path'])
        dbapi = db_api.db_interface()
        self.rev_files_list.sort(key=dbapi.get_first_date_by_filename, reverse=True)  
        return self.rev_files_list


    def deploy_selected_flashcards_to_load_handler(self):
        selected_index = self.flashcard_files_qlist.currentRow()
        
        if selected_index < 0: return # safety-check

        # Deterime if selected file is rev or lng by its position in the list
        if selected_index < len(self.lng_files_list):
            corresponing_path = self.config['lngs_path']
        else:
            corresponing_path = self.config['revs_path']

        concatenated_lists = self.lng_files_list + self.rev_files_list
        file_path = corresponing_path + concatenated_lists[selected_index]
        
        self.main_window.initiate_flashcards(file_path)

