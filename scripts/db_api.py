import pandas as pd
from utils import *

config = load_config()
REV_DB_PATH = config['db_path']


def create_record(signature, words_total, positives):
    # Saves revision params to rev_db
    timestamp = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    with open(REV_DB_PATH,'a') as fd:
        fd.write(';'.join([timestamp, signature, str(words_total), str(positives)])+'\n')
    print('Record created succcessfully')


class db_interface():
    # Used for convenient quering of DB

    def __init__(self):
        self.db = pd.read_csv(REV_DB_PATH, encoding='utf-8', sep=';')
       

    def get_unique_signatures(self):
        return self.db['SIGNATURE'].drop_duplicates()


    def get_sum_repeated(self, signature):
        # -1 = initial record correction
        return self.db[self.db['SIGNATURE'] == signature].count()[0] - 1
    

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

    def get_timedelta_from_creation(self, signature):
        try:
            d = self.db[self.db['SIGNATURE'] == signature]['TIMESTAMP'].iloc[0]
            first_date = make_datetime(d)
            today = make_todaytime()
            return today - first_date
        except:
            return None


    def get_timedelta_from_last_rev(self, signature):
        try:
            d = self.db[self.db['SIGNATURE'] == signature]['TIMESTAMP'].iloc[-1]
            last_date = make_datetime(d)
            today = make_todaytime()
            return today - last_date
        except:
            return None


    def get_newest_record(self, lng=None):
        # returns last record from db
        # optionally matching the lng provided
        # if NA - returns last record
        match = ''
        
        for i in range(self.db.shape[0]-1, -1, -1):
            if self.db['SIGNATURE'].iloc[i][4:6] == lng:
                match =  self.db['SIGNATURE'].iloc[i]
                break

        if match == '':
            print('File Not Found')
        
        return match


    def get_chart_values(self, signature):
        # Used for stat chart
        res = self.db[(self.db['SIGNATURE'] == signature) & (self.db['POSITIVES'] != 0)]['POSITIVES'].values.tolist()
        return res


    def get_chart_dates(self, signature):
        # Used for stat chart
        res = self.db[(self.db['SIGNATURE'] == signature) & (self.db['POSITIVES'] != 0)]['TIMESTAMP'].values.tolist()
        return res
