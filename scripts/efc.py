import PyQt5.QtWidgets as widget
from PyQt5 import QtGui
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
        self.font_button_size = int(self.config['efc_button_font_size'])
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


    def efc_function(self, last_date, total_words, last_positives, repeated_times, initial_date):
            # based on Ebbinghaus Forgetting Curve
            # Returns True if a revision is advised to be reviewed

            time_delta = (make_todayte() - make_date(last_date)).days
            time_delta_from_initial = (make_todayte() - make_date(initial_date)).days
            
            # returning 0 always meets efc criteria
            if time_delta_from_initial == 0 and (time_delta_from_initial + repeated_times == 0): # initial day
                return 0
            elif time_delta_from_initial <= 2 and time_delta != 0:  # day 1 and 2
                return 0
            else:  # employ forgetting curve
                pos_share = last_positives/total_words if last_positives is not None else 1
                x1, x2, x3, x4 = 2.039, -4.566, -12.495, -0.001
                s = (repeated_times**x1 + pos_share*x2) - (x3*exp(total_words*x4))
                efc = exp(-time_delta/s)
                return efc


    def get_recommendations(self):
        
        # unique signatures from rev_db - only for existing files
        unique_signatures = [s for s in self.db_interface.get_unique_signatures() 
                                if s + '.csv' in listdir(self.config['revs_path'])]
        reccommendations = list()

        if 'recommend_new' in self.config['optional'].split('|'):
            reccommendations.extend(self.is_it_time_for_something_new(unique_signatures))


        # get parameters and efc_function result for each unique signature
        # filter on the go
        rev_table_data = list()
        for signature in unique_signatures:
            last_date = self.db_interface.get_last_date(signature)
            initial_date = self.db_interface.get_first_date(signature)
            repeated_times = self.db_interface.get_sum_repeated(signature)
            total = self.db_interface.get_total_words(signature)
            last_positives = self.db_interface.get_last_positives(signature)
            efc = self.efc_function(last_date, total, last_positives, repeated_times, initial_date)
            efc_critera_met = efc < 0.80

            days_from_last_rev = (make_todayte() - make_date(last_date)).days
            rev_table_data.append([signature, days_from_last_rev, str(days_from_last_rev), round(efc, 2)])

            if efc_critera_met:
                reccommendations.append(signature)

        # Table showing revs params
        print('REV_NAME             | DAYS AGO | EFC')
        rev_table_data.sort(key=lambda x: x[1])
        for rev in rev_table_data:
            print(f'{rev[0]} | {rev[1]}{" " * (9-len(rev[2]))}| {rev[3]}')
            
        return reccommendations


    def load_selected(self):
        # safety-check if item is selected
        if self.recommendation_list.currentItem() is None: return

        selected_li = self.recommendation_list.currentItem().text()
        try:
            self.main_window.del_side_window()

            # Check if selected item is a suggestion to create a new revision
            if selected_li in self.paths_to_suggested_lngs.keys():
                path = f"{self.config['lngs_path']}/{self.paths_to_suggested_lngs[selected_li]}"
            else:
                path = f"{self.config['revs_path']}/" + str(selected_li) + '.csv'
            
            self.main_window.load_from_path(path)
                     
        except FileNotFoundError:
            print('Requested File Not Found')
    

    def is_it_time_for_something_new(self, unique_signatures):
        # Periodically reccommend to create new revision for every lng
        # lng and period are specified in config.

        lngs = self.config['languages'].split('|')
        new_reccommendations = list()

        unique_signatures.sort(key=get_date_from_signature, reverse=True)  

        # For each lng calculate days diff from initial date of 
        # the newest revision and check if it's greater than 
        # parameter specified in config
        for lng in lngs:
            for signature in unique_signatures:
                if lng.upper() in signature:
                    initial_date = self.db_interface.get_first_date(signature)
                    time_delta = (make_todayte() - make_date(initial_date)).days
                    if time_delta >= int(self.config['days_to_new_rev']):
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
        
        


