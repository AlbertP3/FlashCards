import pandas as pd
from pandas.core.frame import DataFrame
from os import listdir
from datetime import datetime, time



# Check if DB file already exists else create new one
rev_db_name = 'rev_db.csv'
if rev_db_name not in [f for f in listdir('.')]:
    print('Initializing new Database')
    DataFrame().to_csv(rev_db_name)


def create_record(signature, words_total, positives):
    timestamp = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    with open(rev_db_name,'a') as fd:
        fd.write(';'.join([timestamp, signature, str(words_total), str(positives),'\n']))
    print('Record created succcessfully')


def get_db():
    return pd.read_csv(rev_db_name, encoding='utf-8')