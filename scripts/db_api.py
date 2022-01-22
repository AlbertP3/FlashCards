from numpy import positive
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


    def __init__(self):
        self.db = pd.read_csv(REV_DB_PATH, encoding='utf-8', sep=';')
       

    def get_unique_signatures(self):
        return self.db['SIGNATURE'].drop_duplicates()


    def get_sum_repeated(self, signature):
        # -1 = initial record correction
        return self.db[self.db['SIGNATURE'] == signature].count()[0] - 1
    

    def get_last_score(self, signature):
        try:
            positives = self.get_last_positives(signature)
            total = self.get_total_words(signature)
            return positives/total
        except:
            return None

    
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
            first_date = self.db[self.db['SIGNATURE'] == signature]['TIMESTAMP'].iloc[0]
            return date(int(first_date[6:10]), int(first_date[0:2]), int(first_date[3:5]))
        except:
            # occurs if file in dir was never recorded in DB
            # returning some date avoids errors down the line
            return date(1900, 1, 1)


    def get_first_date_by_filename(self, filename_with_extension):
            return self.get_first_date(filename_with_extension.split('.')[0])


    def get_last_date(self, signature):
        try:
            last_date = self.db[self.db['SIGNATURE'] == signature]['TIMESTAMP'].iloc[-1]
            return date(int(last_date[6:10]), int(last_date[0:2]), int(last_date[3:5]))
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


    def get_latest_record_signature(self, lng):
        # returns last record from db
        # optionally matching the lng provided
        # if NA - returns last record
        
        match = ''
        for i in range(self.db.shape[0]-1, -1, -1):
            if lng in self.db['SIGNATURE'].iloc[i]:
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
