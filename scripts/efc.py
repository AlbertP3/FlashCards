import PyQt5.QtWidgets as widget
from PyQt5 import QtGui
from PyQt5.QtCore import Qt
import db_api
from utils import *
from math import exp
import gui_main
from os import listdir



class EFC(widget.QWidget):

    def __init__(self, main_window:gui_main.main_window):

        # Configuration
        super(EFC, self).__init__(None)
        self.main_window = main_window
        self.initial_repetitions = 2
        self.paths_to_suggested_lngs = dict()

       
    def get_efc_layout(self):
        # Get newest data
        self.config = load_config()
        self.db_interface = db_api.db_interface()

        self.arrange_window()
        
        # Window Parameters
        self.buttons_height = 45

        # Fill List Widgets
        self.recommendations_list = self.get_recommendations()
        [self.recommendation_list.addItem(str(r)) for r in self.recommendations_list]

        return self.efc_layout


    def arrange_window(self):
   
        # Style
        self.textbox_stylesheet = (self.config['textbox_style_sheet'])
        self.button_style_sheet = self.config['button_style_sheet']
        self.font = self.config['font']
        self.font_button_size = self.config['efc_button_font_size']
        self.button_font = QtGui.QFont(self.font, self.font_button_size)
        self.textbox_width = 250
        self.textbox_height = 200
        self.buttons_height = 45

        # Elements
        self.efc_layout = widget.QGridLayout()
        self.efc_layout.addWidget(self.create_recommendations_list(), 0, 0)
        self.efc_layout.addWidget(self.create_load_button(), 1, 0, 1, 1)


    def create_recommendations_list(self):
        self.recommendation_list = widget.QListWidget(self)
        self.recommendation_list.setFixedWidth(self.textbox_width)
        self.recommendation_list.setFont(self.button_font)
        self.recommendation_list.setStyleSheet(self.textbox_stylesheet)
        return self.recommendation_list


    def create_load_button(self):
        self.load_button = widget.QPushButton(self)
        self.load_button.setFixedHeight(self.buttons_height)
        self.load_button.setFixedWidth(self.textbox_width)
        self.load_button.setFont(self.button_font)
        self.load_button.setText('Load')
        self.load_button.setStyleSheet(self.button_style_sheet)
        self.load_button.clicked.connect(self.load_selected)
        return self.load_button


    def efc_function(self, last_date, total_words, last_positives, repeated_times):
            # Returns True if a revision is advised to be reviewed
            # Verdict is based on efc function - which needs to be fine-tuned #todo

            threshold = 0.8
            time_delta = (make_todayte() - make_date(last_date)).days
            pos_share = last_positives/total_words if last_positives is not None else 1

            s = (repeated_times**2.137 + pos_share*1.618) - (1.681*exp(total_words*0.042))
            efc = exp(-time_delta/s)

            return efc < threshold


    def get_recommendations(self):
        
        # unique signatures from rev_db - only for existing files
        unique_signatures = [s for s in self.db_interface.get_unique_signatures() 
                                if s + '.csv' in listdir(self.config['revs_path'])]
    
        # get parameters and efc_function result for each unique signature
        # filter on the go
        reccommendations = list()
        reccommendations.extend(self.is_it_time_for_something_new(unique_signatures))

        # temp solution - print whole table to terminal (2 lines of code)
        # print('REV_NAME             | DAYS AGO')

        for signature in unique_signatures:
            last_date = self.db_interface.get_last_date(signature)
            repeated_times = self.db_interface.get_sum_repeated(signature)
            total = self.db_interface.get_total_words(signature)
            last_positives = self.db_interface.get_last_positives(signature)
            efc_critera_met = self.efc_function(last_date, total, last_positives, repeated_times)
            
            # print(f'{signature} | {(make_todayte() - make_date(last_date)).days}')

            if efc_critera_met:
                reccommendations.append(signature)

        return reccommendations


    def load_selected(self):
        selected_li = self.recommendation_list.currentItem().text()
        try:
            self.main_window.del_side_window()

            # loading rev file
            if selected_li not in self.paths_to_suggested_lngs.keys():
                self.main_window.load_button_click(f"{self.config['revs_path']}/" + str(selected_li) + '.csv')
            else:
            # loading lng file
                self.main_window.load_button_click(
                     f"{self.config['lngs_path']}\{self.paths_to_suggested_lngs[selected_li]}")
                     
        except FileNotFoundError:
            print('Requested File Not Found')
    

    def is_it_time_for_something_new(self, unique_signatures):
        # Periodically reccommend to create new revision for every
        # lng specified in config.

        lngs = self.config['languages'].split('|')
        new_reccommendations = list()

        unique_signatures.sort(key=lambda e: date(int(e[10:12]), int(e[6:8]), int(e[8:10])), reverse=True)  

        for lng in lngs:
            for signature in unique_signatures:
                if signature[4:6] == lng.upper():
                    initial_date = self.db_interface.get_first_date(signature)
                    time_delta = (make_todayte() - make_date(initial_date)).days
                    if time_delta >= self.config['days_to_new_rev']:
                        new_reccommendations.append(self.get_reccommendation_text(lng))
                    break
        return new_reccommendations


    def get_reccommendation_text(self, lng):
        # get announcements and paths to the corresponding files
        # adding keys to dictionary facilitates matching with text in efc list

        if lng == 'EN':
            text = 'Oi mate, take a gander'
            self.paths_to_suggested_lngs[text] = get_most_similar_file(config['lngs_path'], 'EN')
            return text
        elif lng == 'RU':
            text = 'давай товарищ, двигаемся!'
            self.paths_to_suggested_lngs[text] = get_most_similar_file(config['lngs_path'], 'RU')
            return text
        
        


