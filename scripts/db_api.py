import pandas as pd
from os import listdir
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter
from utils import *

config = load_config()

# Check if DB file already exists else create new one
rev_db_name = 'rev_db.csv'
rev_db_path = config['resources_path'] + '\\' + rev_db_name
if rev_db_name not in [f for f in listdir(config['resources_path'])]:
    print('Initializing new Database')
    pd.DataFrame(columns=['TIMESTAMP','SIGNATURE','TOTAL','POSITIVES']).to_csv(config['resources_path'] + '\\' + rev_db_name)


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

    def get_last_date(self, signature):
        try:
            return self.db[self.db['SIGNATURE'] == signature]['TIMESTAMP'].iloc[-1]
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

    def get_newest_record(self, lng=None):
        # returns last record from db optionally
        # matching the lng provided
        # if NA - returns last record
        match = ''
        
        for i in range(self.db.shape[0]-1, -1, -1):
            if self.db['SIGNATURE'].iloc[i][4:6] == lng:
                match =  self.db['SIGNATURE'].iloc[i]

        if match == '':
            match = self.db['SIGNATURE'].iloc[-1]
        
        return match


    def get_chart_values(self, signature):
        res = self.db[(self.db['SIGNATURE'] == signature) & (self.db['POSITIVES'] != 0)]['POSITIVES'].values.tolist()
        return res


    def get_chart_dates(self, signature):
        res = self.db[(self.db['SIGNATURE'] == signature) & (self.db['POSITIVES'] != 0)]['TIMESTAMP'].values.tolist()
        return res
