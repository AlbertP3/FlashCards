from matplotlib.transforms import Bbox
from numpy import sign
import pandas as pd
from pandas.core.frame import DataFrame
from os import listdir
from datetime import datetime, date
import matplotlib.pyplot as plt
import numpy as np
from logic import *

config = load_config()

# Check if DB file already exists else create new one
rev_db_name = 'rev_db.csv'
if rev_db_name not in [f for f in listdir('.')]:
    print('Initializing new Database')
    DataFrame().to_csv(rev_db_name)


def create_record(signature, words_total, positives):
    timestamp = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    with open(rev_db_name,'a') as fd:
        fd.write(';'.join([timestamp, signature, str(words_total), str(positives)])+'\n')
    print('Record created succcessfully')



class db_interface():

    def __init__(self):
        self.db = pd.read_csv(rev_db_name, encoding='utf-8', sep=';')
       

    def get_sum_repeated(self, signature):
        return self.db[self.db['SIGNATURE'] == signature].count()[0]
    

    def get_last_positives_share(self, signature):
        return self.db[self.db['SIGNATURE'] == signature]['POSITIVES'].iloc[-1]
    

    def get_first_date(self, signature):
        return self.db[self.db['SIGNATURE'] == signature]['TIMESTAMP'].iloc[0]
    

    def get_days_ago(self, signature):
        d = self.db[self.db['SIGNATURE'] == signature]['TIMESTAMP'].iloc[0]
        first_date = make_datetime(d)
        today = make_todaytime()
        return today - first_date

        
    def get_positives_chart(self, signature):
        dates = self.db[self.db['SIGNATURE'] == signature]['TIMESTAMP'].values.tolist()
        values = self.db[self.db['SIGNATURE'] == signature]['POSITIVES'].values.tolist()
        sum_repeated = str(self.get_sum_repeated(signature))
        last_pos_share = str(self.get_last_positives_share(signature))
        first_date = str(self.get_first_date(signature))
        days_ago = str(self.get_days_ago(signature))

        # Chart Configuration
        fig, axs = plt.subplots(2,1, num=signature, gridspec_kw={'height_ratios': [2, 1]})
        plt.rcParams.update({'text.color': config['font_color'],
                            'axes.labelcolor':config['font_color']})
        fig.patch.set_facecolor(config['stat_background_color'])
        axs[0].set_facecolor(config['stat_chart_background_color'])
        axs[1].set_facecolor(config['stat_chart_background_color'])
        plt.rcParams['font.family'] = config['font']
        plt.setp(axs[0].xaxis.get_majorticklabels(), rotation=45)
        bar_color = [config['stat_bar_color'] for _ in range(len(dates))]
        for i in range(len(dates)):
            axs[0].bar(dates[i][:5] + '/' + dates[i][8:10], values[i], color=bar_color)
        
        axs[1].axis('off')
        table = axs[1].table(cellText=[[sum_repeated], [last_pos_share], [first_date], [days_ago]],
                rowLabels=['Repeated Times', 'last_pos_share', 'first_date_mdy', 'time_ago'],
                loc='center', cellLoc='right',
                bbox = [0.4, 0.4, 0.35, 0.8])  #  x,y,w,h
        table.scale(1, 2)
        table.auto_set_column_width(col=list(range(2)))
        
        plt.tight_layout(pad=1.0)
        plt.show()
    

