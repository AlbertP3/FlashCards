# What it does:
# 1. Open window showing recommended revisions inline with remaining revisions
# 2. Clicking on the recommendation loads chosen file

import PyQt5.QtWidgets as widget
from PyQt5 import QtGui
import db_api
from logic import load_config
from utils import *
from math import exp, log10



class EFC(widget.QWidget):

    def __init__(self, parent=None):

        # Configuration
        self.config = load_config()
        super(EFC, self).__init__(parent)
        self.initial_repetitions = 2

        # Window Parameters
        self.left = 10
        self.top = 10
        self.width = 200
        self.height = 250
        self.buttons_height = 45

        self.arrange_window()


    def arrange_window(self):
        self.setWindowTitle('EFC')
        self.setWindowIcon(QtGui.QIcon('icon.png'))
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

    
    def get_recommendations_and_remaining(self):
        recommendations, remaining = None, None
        # ToDo - query
        return recommendations, remaining


    def efc_function(self, date, total_words, positives):
        time_delta = make_todayte - make_date(date)
        n = exp(0.007 * (total_words-30)) * 1.6
        pos_share = positives/total_words

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

    
    def load_selected(self):
        pass


