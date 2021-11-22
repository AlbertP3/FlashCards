import pandas as pd
from pandas.core.frame import DataFrame
from os import listdir
import matplotlib.pyplot as plt
from utils import *

config = load_config()

# Check if DB file already exists else create new one
rev_db_name = 'rev_db.csv'
rev_db_path = config['resources_path'] + '\\' + rev_db_name
if rev_db_name not in [f for f in listdir(config['resources_path'])]:
    print('Initializing new Database')
    DataFrame(columns=['TIMESTAMP','SIGNATURE','TOTAL','POSITIVES']).to_csv(config['resources_path'] + '\\' + rev_db_name)


def create_record(signature, words_total, positives):
    timestamp = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    with open(rev_db_path,'a') as fd:
        fd.write(';'.join([timestamp, signature, str(words_total), str(positives)])+'\n')
    print('Record created succcessfully')



class db_interface():
    # Used for convenient quering (templates) of DB

    def __init__(self):
        self.db = pd.read_csv(rev_db_path, encoding='utf-8', sep=';')
       

    def get_unique_signatures(self):
        return self.db['SIGNATURE'].drop_duplicates()


    def get_sum_repeated(self, signature):
        return self.db[self.db['SIGNATURE'] == signature].count()[0]
    

    def get_last_positives(self, signature):
        try:
            return self.db[(self.db['SIGNATURE'] == signature) & (self.db['POSITIVES'] != 0)]['POSITIVES'].iloc[-1]
        except:
            return None

    def get_total_words(self, signature):
        try:
            return self.db[self.db['SIGNATURE'] == signature]['TOTAL'].iloc[-1]
        except:
            return None

    def get_first_date(self, signature):
        try:
            return self.db[self.db['SIGNATURE'] == signature]['TIMESTAMP'].iloc[0]
        except:
            return None

    def get_days_ago(self, signature):
        try:
            d = self.db[self.db['SIGNATURE'] == signature]['TIMESTAMP'].iloc[0]
            first_date = make_datetime(d)
            today = make_todaytime()
            return today - first_date
        except:
            return None

        
    def get_positives_chart(self, signature):
        # Display statistics for specific file (signature)
        # checking sum_repeated value in order to avoid errors
        # when rev not in DB and still show the (empty) chart

        sum_repeated = str(self.get_sum_repeated(signature))
        
        if sum_repeated != 0:
            dates = self.db[(self.db['SIGNATURE'] == signature) & (self.db['POSITIVES'] != 0)]['TIMESTAMP'].values.tolist()
            values = self.db[(self.db['SIGNATURE'] == signature) & (self.db['POSITIVES'] != 0)]['POSITIVES'].values.tolist()
            last_pos_share = str(self.get_last_positives(signature))
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

        if sum_repeated != 0:
            bar_color = [config['stat_bar_color'] for _ in range(len(dates))]
            for i in range(len(dates)):
                axs[0].bar(dates[i][:5] + '/' + dates[i][8:10], values[i], color=bar_color)
        
        # Table Configuration
        axs[1].axis('off')
        table = axs[1].table(cellText=[[sum_repeated], [last_pos_share], [first_date], [days_ago]],
                rowLabels=['Repeated Times', 'last_pos_share', 'first_date_mdy', 'time_ago'],
                loc='center', cellLoc='right',
                bbox = [0.4, 0.4, 0.35, 0.8])  #  x,y,w,h
        table.scale(1, 2)
        table.auto_set_column_width(col=list(range(2)))
        
        # Execute
        plt.tight_layout(pad=1.0)
        plt.show()
    

