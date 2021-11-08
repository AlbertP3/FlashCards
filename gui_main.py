import sys

from PyQt5 import QtCore
from utils import *
import logic
import PyQt5.QtWidgets as widget

from PyQt5 import QtGui
import pandas as pd


def __launch_main_window():
    # keep a reference to the opened window, 
    # otherwise it goes out of scope and is garbage collected
    mw = main_window()
    mw.show()
    return mw


class main_window(widget.QWidget):
    # Everything user sees is a widget
    # self.load_button.clicked.connect(self.dummy_insert) <- func w/o args

    def __init__(self):
        super().__init__()

        # Flashcards parameters
        self.revmode = 'OFF'
        self.total_words = 0
        self.current_index = 0
        self.dataset = None
        self.side = 0
        self.positives = 0
        self.negatives = 0
        self.words_back = 0

        # Window Parameters
        self.left = 10
        self.top = 10
        self.width = 475
        self.height = 450
        self.textbox_height = 280
        self.buttons_height = 45

        # Set Parameters
        self.setWindowTitle('LlamaLearning')
        self.setGeometry(self.left, self.top, self.width, self.height)

        # Layout & Style
        self.layout = widget.QGridLayout()
        self.setLayout(self.layout)
        self.font = 'Helvetica'
        self.font_button_size = 14
        self.font_textbox_size = 32
        self.textbox_font = QtGui.QFont(self.font, self.font_textbox_size)
        self.button_font = QtGui.QFont(self.font, self.font_button_size)
        
        # see available styles
        # print(PyQt5.QtWidgets.QStyleFactory.keys())
        # self.setStyle(widget.QStyleFactory.create('WindowsXP'))

        self.setStyleSheet("""
        background-color: #979dac; 
        margin:0px; 
        border:1px solid #202020;
        padding:0px;
        """)
        
        self.textbox_stylesheet = ('''
            color: #3a3a3a; 
            background-color: #cfdbd5;
            border-radius: 5px;
            line-height: 12%;
            ''')

        self.button_style_sheet = ('''
        background-color: #7d8597;
        color: #e8e8e8;
        border-radius: 5px;
        ''')

        self.layout_first_row = widget.QGridLayout()
        self.layout_second_row = widget.QGridLayout()
        self.layout_third_row = widget.QGridLayout()
        self.layout_fourth_row = widget.QGridLayout()
        self.layout_next_navigation = widget.QGridLayout()

        self.layout.addLayout(self.layout_first_row, 0, 0)
        self.layout.addLayout(self.layout_second_row, 1, 0)
        self.layout.addLayout(self.layout_third_row, 2, 0)
        self.layout.addLayout(self.layout_fourth_row, 3, 0)

        # Widgets
        self.layout_first_row.addWidget(self.textbox(), 0, 0)

        self.layout_second_row.addWidget(self.create_prev_button(), 0, 0)
        self.layout_second_row.addWidget(self.create_reverse_button(), 0, 1)
        self.layout_second_row.addLayout(self.layout_next_navigation, 0, 2)
        
        self.layout_next_navigation.addWidget(self.create_next_button(), 0, 0)
        self.create_positive_button().setParent(None)
        self.create_negative_button().setParent(None)

        self.layout_third_row.addWidget(self.create_load_button(), 2, 0)
        self.layout_third_row.addWidget(self.create_del_button(), 2, 1)
        self.layout_third_row.addWidget(self.create_efc_button(), 2, 2)
        self.layout_third_row.addWidget(self.create_save_button(), 2, 3)

        self.layout_fourth_row.addWidget(self.create_score_button(), 3, 0)
        self.layout_fourth_row.addWidget(self.create_settings_button(), 3, 1)
        self.layout_fourth_row.addWidget(self.create_load_again_button(), 3, 2)
        self.layout_fourth_row.addWidget(self.create_words_button(), 3, 3)
        self.layout_fourth_row.addWidget(self.create_revmode_button(), 3, 4)
        

        # Execute
        self.center()
        self.show()
    

    def textbox(self):
        self.textbox = widget.QTextEdit(self)
        self.textbox.setFixedHeight(self.textbox_height)
        self.textbox.setFont(self.textbox_font)
        self.textbox.setStyleSheet(self.textbox_stylesheet)
        self.textbox.setAlignment(QtCore.Qt.Alignment(QtCore.Qt.AlignCenter))
        return self.textbox


    def create_load_button(self):
        self.load_button = widget.QPushButton('Load', self)
        self.load_button.setFixedHeight(self.buttons_height)
        self.load_button.setFont(self.button_font)
        self.load_button.setText('Load')
        self.load_button.clicked.connect(self.load_button_click)
        self.load_button.setStyleSheet(self.button_style_sheet)
        return self.load_button

    def create_prev_button(self):
        self.prev_button = widget.QPushButton(self)
        self.prev_button.setFixedHeight(self.buttons_height)
        self.prev_button.setFont(self.button_font)
        self.prev_button.setText('Prev')
        self.prev_button.clicked.connect(self.click_prev)
        self.prev_button.setStyleSheet(self.button_style_sheet)
        return self.prev_button

    def create_next_button(self):
        self.next_button = widget.QPushButton(self)
        self.next_button.setFixedHeight(self.buttons_height)
        self.next_button.setFont(self.button_font)
        self.next_button.setText('Next')
        self.next_button.clicked.connect(self.click_next)
        self.next_button.setStyleSheet(self.button_style_sheet)
        return self.next_button
    
    def create_positive_button(self):
        self.positive_button = widget.QPushButton(self)
        self.positive_button.setFixedHeight(self.buttons_height)
        self.positive_button.setFont(self.button_font)
        self.positive_button.setText('✔️')
        self.positive_button.clicked.connect(self.positive_click)
        self.positive_button.setStyleSheet(self.button_style_sheet)
        return self.positive_button

    def create_negative_button(self):
        self.negative_button = widget.QPushButton(self)
        self.negative_button.setFixedHeight(self.buttons_height)
        self.negative_button.setFont(self.button_font)
        self.negative_button.setText('❌')
        self.negative_button.clicked.connect(self.negative_click)
        self.negative_button.setStyleSheet(self.button_style_sheet)
        return self.negative_button

    def positive_click(self):
        if self.current_index + 1 <= self.total_words and self.words_back == 0:
            self.positives+=1
        self.click_next()
    
    def negative_click(self):
        if self.current_index + 1 <= self.total_words and self.words_back == 0:
            self.negatives+=1
        self.click_next()

    def create_reverse_button(self):
        self.reverse_button = widget.QPushButton(self)
        self.reverse_button.setFixedHeight(self.buttons_height)
        self.reverse_button.setFont(self.button_font)
        self.reverse_button.setText('Reverse')
        self.reverse_button.clicked.connect(self.reverse_side)
        self.reverse_button.setStyleSheet(self.button_style_sheet)
        return self.reverse_button

    def create_score_button(self):
        self.score_button = widget.QPushButton(self)
        self.score_button.setFixedHeight(self.buttons_height)
        self.score_button.setFont(self.button_font)
        self.score_button.setText('<>')
        self.score_button.setStyleSheet(self.button_style_sheet)
        return self.score_button

    def create_settings_button(self):
        self.settings_button = widget.QPushButton(self)
        self.settings_button.setFixedHeight(self.buttons_height)
        self.settings_button.setFont(self.button_font)
        self.settings_button.setText('⚙')
        self.settings_button.setStyleSheet(self.button_style_sheet)
        return self.settings_button

    def create_save_button(self):
        self.save_button = widget.QPushButton(self)
        self.save_button.setFixedHeight(self.buttons_height)
        self.save_button.setFont(self.button_font)
        self.save_button.setText('Save')
        self.save_button.setStyleSheet(self.button_style_sheet)
        return self.save_button

    def create_del_button(self):
        self.del_button = widget.QPushButton(self)
        self.del_button.setFixedHeight(self.buttons_height)
        self.del_button.setFont(self.button_font)
        self.del_button.setText('🗑')
        self.del_button.setStyleSheet(self.button_style_sheet)
        return self.del_button

    def create_load_again_button(self):
        self.load_again_button = widget.QPushButton(self)
        self.load_again_button.setFixedHeight(self.buttons_height)
        self.load_again_button.setFont(self.button_font)
        self.load_again_button.setText('⟳')
        self.load_again_button.setStyleSheet(self.button_style_sheet)
        return self.load_again_button

    def create_revmode_button(self):
        self.revmode_button = widget.QPushButton(self)
        self.revmode_button.setFixedHeight(self.buttons_height)
        self.revmode_button.setFont(self.button_font)
        self.revmode_button.setText('RM:{}'.format(self.revmode))
        self.revmode_button.clicked.connect(self.change_revmode)
        self.revmode_button.setStyleSheet(self.button_style_sheet)
        return self.revmode_button

    def create_efc_button(self):
        self.efc_button = widget.QPushButton(self)
        self.efc_button.setFixedHeight(self.buttons_height)
        self.efc_button.setFont(self.button_font)
        self.efc_button.setText('📜')
        self.efc_button.setStyleSheet(self.button_style_sheet)
        return self.efc_button

    def create_words_button(self):
        self.words_button = widget.QPushButton(self)
        self.words_button.setFixedHeight(self.buttons_height)
        self.words_button.setFont(self.button_font)
        self.words_button.setStyleSheet(self.button_style_sheet)
        self.words_button.setText('-')
        return self.words_button


    def reverse_side(self):
        self.side = 1 - self.side
        self.insert_text(self.get_current_card())
        

    def append_current_index(self):
        if self.current_index < self.total_words - 1:
            self.current_index += 1
            self.set_words_button_text()


    def decrease_current_index(self):
        if self.current_index >= 1:
            self.current_index -= 1
            self.set_words_button_text()


    def set_words_button_text(self):
        self.words_button.setText('{}/{}'.format(self.current_index+1, self.total_words))


    def click_next(self):
        if self.current_index < self.total_words:
            self.update_score()
            self.append_current_index()
            if self.words_back > 0:
                self.words_back-=1
            self.insert_text(self.get_current_card())


    def click_prev(self):
        self.decrease_current_index()
        self.words_back+=1
        self.insert_text(self.get_current_card())


    def center(self):
        frame_geo = self.frameGeometry()
        target_pos = widget.QDesktopWidget().availableGeometry().center()
        frame_geo.moveCenter(target_pos)
        self.move(frame_geo.topLeft())


    def insert_text(self, text, default_font=16):
        dynamic_font_size = 32 - int(len(text)/12)
        self.font_textbox_size = dynamic_font_size if dynamic_font_size >= 8 else default_font
        self.textbox_font = QtGui.QFont(self.font, self.font_textbox_size)
        self.textbox.setFont(self.textbox_font)
        self.textbox.setText(text)
        padding = 90 - len(text)*0.6
        padding = max(0, padding)
        self.textbox.setStyleSheet('''{} 
                                    padding-top: {}%;'''.format(self.textbox_stylesheet, padding))
        self.textbox.setAlignment(QtCore.Qt.AlignCenter)


    def update_score(self):
        if self.revmode == 'ON':
            score = self.positives / (self.positives + self.negatives)
            score = round(score*100,0)
            self.score_button.setText('{}%'.format(int(score)))
        else:
            self.score_button.setText('<>')

    def change_revmode(self):
        self.revmode = 'ON' if self.revmode == 'OFF' else 'OFF'
        self.revmode_button.setText('RM:{}'.format(self.revmode))
        
        # show/hide buttons
        if self.revmode == 'ON':
            self.next_button.setParent(None)
            self.layout_next_navigation.addWidget(self.negative_button, 0, 0)
            self.layout_next_navigation.addWidget(self.positive_button, 0, 1)
        else:
            self.positive_button.setParent(None)
            self.negative_button.setParent(None)
            self.layout_next_navigation.addWidget(self.next_button, 0, 0)
            

    def load_button_click(self):
        self.dataset, succcess = logic.load_dataset()
        if succcess:
            self.total_words = self.dataset.shape[0]
            self.set_words_button_text()
            self.insert_text(self.get_current_card())


    def get_current_card(self):
        return self.dataset.iloc[self.current_index, self.side]
                

def launch():
    # [] or sys.argv represent cmd lines passed to the application
    app = widget.QApplication([])
    window = __launch_main_window()
    app.exec()
    return window


if __name__ == '__main__':
    window = launch()