import PyQt5.QtWidgets as widget
from PyQt5 import QtGui
import db_api
from utils import *
from math import exp, log10
import gui_main
from os import listdir



class EFC(widget.QWidget):

    def __init__(self, main_window:gui_main.main_window):

        # Configuration
        self.config = load_config()
        super(EFC, self).__init__(None)
        self.main_window = main_window
        self.initial_repetitions = 2

        # Window Parameters
        self.left = 10
        self.top = 10
        self.width = 280
        self.height = 250
        self.buttons_height = 45

        self.arrange_window()
        
        # Fill List Widgets
        self.recommendations_and_remaining_list = self.get_recommendations_and_remaining()
        [self.recommendation_list.addItem(str(r[0])) for r in self.recommendations_and_remaining_list]
        [self.remaining_revs_list.addItem(str('{:.0f}'.format(r[1]))) for r in self.recommendations_and_remaining_list]


    def arrange_window(self):
        self.setWindowTitle('EFC')
        self.setWindowIcon(QtGui.QIcon(self.config['resources_path'] + '\\icon.png'))
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.center()

        # Style
        self.setStyleSheet(self.config['main_style_sheet'])
        self.textbox_stylesheet = (self.config['textbox_style_sheet'])
        self.button_style_sheet = self.config['button_style_sheet']
        self.font = self.config['font']
        self.font_button_size = self.config['efc_button_font_size']
        self.button_font = QtGui.QFont(self.font, self.font_button_size)
        self.textbox_width = 99
        self.textbox_height = 200

        # Elements
        self.layout = widget.QGridLayout()
        self.setLayout(self.layout)
        self.layout.addWidget(self.create_recommendations_list(), 0, 0)
        self.layout.addWidget(self.create_remaining_revs_list(), 0, 1)
        self.layout.addWidget(self.create_load_button(), 1, 0, 1, 2)


    def center(self):
        frame_geo = self.frameGeometry()
        target_pos = widget.QDesktopWidget().availableGeometry().center()
        frame_geo.moveCenter(target_pos)
        self.move(frame_geo.topLeft())


    def create_recommendations_list(self):
        self.recommendation_list = widget.QListWidget(self)
        self.recommendation_list.setFont(self.button_font)
        self.recommendation_list.setStyleSheet(self.textbox_stylesheet)
        return self.recommendation_list


    def create_remaining_revs_list(self):
        self.remaining_revs_list = widget.QListWidget(self)
        self.remaining_revs_list.setFont(self.button_font)
        self.remaining_revs_list.setStyleSheet(self.textbox_stylesheet)
        return self.remaining_revs_list


    def create_load_button(self):
        self.load_button = widget.QPushButton(self)
        self.load_button.setFixedHeight(self.buttons_height)
        self.load_button.setFont(self.button_font)
        self.load_button.setText('Load')
        self.load_button.setStyleSheet(self.button_style_sheet)
        self.load_button.clicked.connect(self.load_selected)
        return self.load_button


    def efc_function(self, initial_date, total_words, last_positives):
            time_delta = (make_todayte() - make_date(initial_date)).days
            n = exp(0.007 * (total_words-30)) * 1.6
            pos_share = last_positives/total_words if last_positives is not None else 1

            if pos_share > 0.92:
                p = -1
            elif pos_share < 0.7:
                p = 1
            else:
                p = 0

            if time_delta != 0:
                return round(n * log10(time_delta)+1, 0) + self.initial_repetitions + p
            else:
                return self.initial_repetitions


    def get_recommendations_and_remaining(self):
        
        # unique signatures from rev_db - only for existing files
        db_interface = db_api.db_interface()
        unique_signatures = [s for s in db_interface.get_unique_signatures() 
                                if s + '.csv' in listdir(self.config['revs_path'])]
    
        # get parameters and efc_function result for each unique signature
        # filter on the go
        recommendations_and_remaining = list()
        for signature in unique_signatures:
            sum_repeated = db_interface.get_sum_repeated(signature)
            first_date = db_interface.get_first_date(signature)
            total = db_interface.get_total_words(signature)
            last_positives = db_interface.get_last_positives(signature)
            efc_revs = self.efc_function(first_date, total, last_positives)
            remaining = efc_revs - sum_repeated

            if remaining > 0:
                recommendations_and_remaining.append([signature, remaining])

        return recommendations_and_remaining


    def load_selected(self):
        file_to_load = self.recommendation_list.currentItem().text()
        try:
            self.main_window.load_button_click(f"{self.config['revs_path']}/" + str(file_to_load) + '.csv')
            self.close()
        except FileNotFoundError:
            print('Requested File Not Found')
        
        


