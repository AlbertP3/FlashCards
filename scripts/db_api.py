import pandas as pd
from utils import *


config = load_config()
REV_DB_PATH = config['db_path'] 
DBAPI_STATUS_DICT = dict()

def post_dbapi(text):
    caller_function = inspect.stack()[1].function
    DBAPI_STATUS_DICT[caller_function] = text

def get_dbapi_dict():
    return DBAPI_STATUS_DICT


def create_record(signature, words_total, positives):
    # Saves revision params to rev_db
    timestamp = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    with open(REV_DB_PATH,'a') as fd:
        fd.write(';'.join([timestamp, signature, str(words_total), str(positives)])+'\n')
    post_dbapi('Record created succcessfully')


class db_interface():

    def __init__(self):
        self.DEFAULT_DATE = datetime(1900, 1, 1)
        self.db = pd.read_csv(REV_DB_PATH, encoding='utf-8', sep=';')
       

    def refresh(self):
        self.__init__()


    def rename_signature(self, old_signature, new_signature):
        self.db = self.db.replace(old_signature, new_signature)
        self.db.to_csv(REV_DB_PATH, encoding='utf-8', sep=';', index=False)
        

    def get_unique_signatures(self):
        return self.db['SIGNATURE'].drop_duplicates()


    def get_sum_repeated(self, signature):
        return self.db[self.db['SIGNATURE'] == signature].count()[0]
    

    def get_last_score(self, signature):
        try:
            positives = self.get_last_positives(signature)
            total = self.get_total_words(signature)
            return positives/total
        except:
            return None

    
    def get_last_positives(self, signature):
        try:
            return self.db[(self.db['SIGNATURE'] == signature)]['POSITIVES'].iloc[-1]
        except:
            return None


    def get_total_words(self, signature):
        try:
            return self.db[self.db['SIGNATURE'] == signature]['TOTAL'].iloc[-1]
        except:
            return None


    def get_max_positives_count(self, signature):
        try:
            positives_list = self.db[(self.db['SIGNATURE'] == signature)]['POSITIVES']
            return positives_list.max()
        except:
            return None


    def get_first_datetime(self, signature):
        try:
            first_date = self.db[self.db['SIGNATURE'] == signature]['TIMESTAMP'].iloc[0]
            return make_datetime(first_date)
        except:
            return self.DEFAULT_DATE
            

    def get_first_date_by_filename(self, filename_with_extension):
            first_date = self.get_first_datetime(filename_with_extension.split('.')[0])
            if first_date is not None:
                return first_date
            else:
                # avoid errors down the line as function is used for sorting
                return self.DEFAULT_DATE


    def get_last_datetime(self, signature):
        try:
            last_date = self.db[self.db['SIGNATURE'] == signature]['TIMESTAMP'].iloc[-1]
            return make_datetime(last_date)
        except:
            return self.DEFAULT_DATE


    def get_timedelta_from_creation(self, signature):
        try:
            first_date = self.get_first_datetime(signature)
            today = make_todaytime()
            return today - first_date
        except:
            return None


    def get_timedelta_from_last_rev(self, signature):
        try:
            last_date = self.get_last_datetime(signature)
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
            post_dbapi('File Not Found')
        
        return match


    def get_chart_values(self, signature):
        # Used for stat chart
        res = self.db[(self.db['SIGNATURE'] == signature) & (self.db['POSITIVES'] != 0)]['POSITIVES'].values.tolist()
        return res


    def get_chart_dates(self, signature):
        # Used for stat chart
        res = self.db[(self.db['SIGNATURE'] == signature) & (self.db['POSITIVES'] != 0)]['TIMESTAMP'].values.tolist()
        return res
