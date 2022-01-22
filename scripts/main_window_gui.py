from PyQt5 import QtCore
from utils import *
from mistakes_dialog import Mistakes
import PyQt5.QtWidgets as widget
from PyQt5 import QtGui
from PyQt5.QtCore import Qt



class main_window_gui(widget.QWidget):

    def __init__(self):
        pass

    def configure_window(self):
        # Window Parameters
        self.LEFT = 10
        self.TOP = 10
        self.DEFAULT_WIDTH = int(self.config['default_width'])
        self.DEFAULT_HEIGHT = int(self.config['default_height'])
        self.TEXTBOX_HEIGHT = int(self.config['textbox_height'])
        self.BUTTONS_HEIGHT = int(self.config['buttons_height'])
        # Set Window Parameters
        self.setWindowTitle('Lama Learning')
        self.setWindowIcon(QtGui.QIcon(self.config['resources_path'] + '/icon.png'))
        self.setGeometry(self.LEFT, self.TOP, self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT)
        # Initialize
        self.center_window()
        self.show()


    def build_layout(self):
        # Layout & Style
        self.layout = widget.QGridLayout()
        self.setLayout(self.layout)
        self.FONT = self.config['font']
        self.FONT_BUTTON_SIZE = int(self.config['font_button_size'])
        self.FONT_TEXTBOX_SIZE = int(self.config['font_textbox_size'])
        self.TEXTBOX_FONT = QtGui.QFont(self.FONT, self.FONT_TEXTBOX_SIZE)
        self.BUTTON_FONT = QtGui.QFont(self.FONT, self.FONT_BUTTON_SIZE)

        # Organize Layout
        self.setStyleSheet(self.config['main_style_sheet'])
        self.textbox_stylesheet = (self.config['textbox_style_sheet'])
        self.button_style_sheet = (self.config['button_style_sheet'])

        self.layout_first_row = widget.QGridLayout()
        self.layout_second_row = widget.QGridLayout()
        self.layout_third_row = widget.QGridLayout()
        self.layout_fourth_row = widget.QGridLayout()
        self.layout_next_navigation = widget.QGridLayout()
        self.side_window_layout = widget.QGridLayout()

        self.layout.addLayout(self.layout_first_row, 0, 0)
        self.layout.addLayout(self.layout_second_row, 1, 0)
        self.layout.addLayout(self.layout_third_row, 2, 0)
        self.layout.addLayout(self.layout_fourth_row, 3, 0)

        # Buttons
        self.next_button = self.create_button('Next', self.click_next)
        self.prev_button = self.create_button('Prev', self.click_prev)
        self.reverse_button = self.create_button('Reverse', self.reverse_side)
        self.load_button = self.create_button('Load', self.load_button_click)
        self.positive_button = self.create_button('✔️', self.click_positive)
        self.negative_button = self.create_button('❌', self.click_negative)
        self.score_button = self.create_button('<>', self.show_mistakes)
        self.settings_button = self.create_button('🎢', self.show_stats)
        self.save_button = self.create_button('Save', self.click_save)
        self.del_button = self.create_button('🗑', self.delete_card)
        self.load_again_button = self.create_button('⟳', self.load_again_click)
        self.revmode_button = self.create_button('RM:{}'.format('OFF'), self.change_revmode)
        self.efc_button = self.create_button('📜', self.show_efc)
        self.words_button = self.create_button('-')

        # Widgets
        self.layout_first_row.addWidget(self.create_textbox(), 0, 0)

        self.layout_second_row.addWidget(self.prev_button, 0, 0)
        self.layout_second_row.addWidget(self.reverse_button, 0, 1)
        self.layout_second_row.addLayout(self.layout_next_navigation, 0, 2)
        
        self.layout_next_navigation.addWidget(self.next_button, 0, 0)
        self.layout_next_navigation.addWidget(self.negative_button, 0, 0)
        self.layout_next_navigation.addWidget(self.positive_button, 0, 1)
        self.negative_button.hide()
        self.positive_button.hide()
        
        self.layout_third_row.addWidget(self.load_button, 2, 0)
        self.layout_third_row.addWidget(self.del_button, 2, 1)
        self.layout_third_row.addWidget(self.efc_button, 2, 2)
        self.layout_third_row.addWidget(self.save_button, 2, 3)

        self.layout_fourth_row.addWidget(self.score_button, 3, 0)
        self.layout_fourth_row.addWidget(self.settings_button, 3, 1)
        self.layout_fourth_row.addWidget(self.load_again_button, 3, 2)
        self.layout_fourth_row.addWidget(self.words_button, 3, 3)
        self.layout_fourth_row.addWidget(self.revmode_button, 3, 4)
            