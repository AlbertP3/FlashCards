import PyQt5.QtWidgets as widget
from PyQt5 import QtGui
from utils import *
import db_api
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.ticker import FormatStrFormatter



class Stats(widget.QWidget):

    def __init__(self, main_window):

        # Configuration
        self.config = load_config()
        super(Stats, self).__init__(None)
        self.main_window = main_window
        self.signature = self.main_window.signature

    def get_stats_layout(self):
        self.config = load_config()
        self.get_data()
        self.get_chart()
        self.get_table()
        self.arrange_window()
        return self.stats_layout


    def arrange_window(self):
        self.stats_layout = widget.QGridLayout()
        self.stats_layout.addWidget(self.canvas, 0, 0)
        self.stats_layout.addWidget(self.table, 1, 0)

    def get_data(self):
        db_interface = db_api.db_interface()

        # get data
        self.chart_values = db_interface.get_chart_values(self.signature)
        self.chart_dates = db_interface.get_chart_dates(self.signature)
        self.formatted_dates = [datetime.strftime(datetime.strptime(date, '%m/%d/%Y, %H:%M:%S'),'%d/%m/%y') for date in self.chart_dates]
        self.last_positives = db_interface.get_last_positives(self.signature)
        self.total_words = db_interface.get_total_words(self.signature)
        self.first_date = db_interface.get_first_date(self.signature)
        self.sum_repeated = str(db_interface.get_sum_repeated(self.signature))
        self.days_ago = db_interface.get_days_ago(self.signature)
        self.last_pos_share = str('{:.0f}%'.format(100*self.last_positives / self.total_words)) if self.last_positives > 0 else 'N/A'

        # Create Dynamic Chain Index
        self.dynamic_chain_index = ['']
        [self.dynamic_chain_index.append('{}({}{})'.format(self.chart_values[x], 
            get_sign( self.chart_values[x] -  self.chart_values[x-1], neg_sign=''), 
            self.chart_values[x] - self.chart_values[x-1])) for x in range(1, len( self.chart_values))]


    def get_chart(self):
        self.figure = Figure(figsize=(5,2))
        self.canvas = FigureCanvas(self.figure)

        ax = self.figure.add_subplot()
        ax.bar(self.formatted_dates, self.chart_values, color=config['stat_bar_color'], 
                edgecolor='#000000', linewidth=0.7, align='center')

        # Labels
        for rect, label in zip(ax.patches, self.dynamic_chain_index):
            height = rect.get_height()
            ax.text(rect.get_x() + rect.get_width()/2, height/2, label, ha="center", va="bottom", 
                    color=self.config['stat_chart_text_color'])

        # Style
        self.figure.set_facecolor(self.config['stat_background_color'])
        ax.set_facecolor(self.config['stat_chart_background_color'])
        ax.yaxis.set_major_formatter(FormatStrFormatter('%.0f'))
        ax.tick_params(colors=self.config['stat_chart_text_color'])
        self.figure.tight_layout(pad=0.1)
        # ax.get_yaxis().set_visible(False)

        self.canvas.draw()        


    def get_table(self):
        self.table = widget.QTableWidget()
        self.table.horizontalHeader().hide()
        self.table.verticalHeader().hide()
        self.table.setColumnCount(3)
        self.table.setRowCount(1)
        self.table.setFixedHeight(45)
        self.table.setStyleSheet(self.config['button_style_sheet'])
        self.table.setFont(QtGui.QFont(self.config['font'], 13))

        # resize rows and columns
        for i in range(self.table.columnCount()):
            self.table.setColumnWidth(i, 166)
        for i in range(self.table.rowCount()):
            self.table.setRowHeight(i, 45)

        self.table.setItem(0, 0, widget.QTableWidgetItem(f'{" "*(len(str(self.sum_repeated))+1)}Repeated {self.sum_repeated} Times'))
        self.table.setItem(0, 1, widget.QTableWidgetItem(f'Last Pos% was {self.last_pos_share}'))
        self.table.setItem(0, 2, widget.QTableWidgetItem(f'Created {str(self.days_ago).split(",")[0]} ago'))
        