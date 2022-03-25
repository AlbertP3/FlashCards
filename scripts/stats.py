from utils import *
import db_api


class stats():

    def __init__(self):
        self.config = load_config()

    
    def get_data_for_current_revision(self):
        db_interface = db_api.db_interface()

        # get data
        self.chart_values = db_interface.get_chart_values(self.signature)
        self.chart_dates = db_interface.get_chart_dates(self.signature)
        self.total_words = db_interface.get_total_words(self.signature)
        self.formatted_dates = [datetime.strftime(datetime.strptime(date, '%m/%d/%Y, %H:%M:%S'),'%d/%m/%y') for date in self.chart_dates]
        self.sum_repeated = str(db_interface.get_sum_repeated(self.signature))
        self.days_ago = format_timedelta(db_interface.get_timedelta_from_creation(self.signature))
        self.last_rev_days_ago = format_timedelta(db_interface.get_timedelta_from_last_rev(self.signature))

        # Create Dynamic Chain Index
        self.dynamic_chain_index = ['']
        [self.dynamic_chain_index.append('{}({}{})'.format(self.chart_values[x], 
            get_sign( self.chart_values[x] -  self.chart_values[x-1], neg_sign=''), 
            self.chart_values[x] - self.chart_values[x-1])) for x in range(1, len( self.chart_values))]


    def get_data_for_progress(self, interval='monthly'):
        date_format_dict = {
            'monthly': '%m/%y',
            'daily': '%d/%m/%y',
        } 

        # get data
        db_interface = db_api.db_interface()
        current_lng = get_lng_from_signature(self.signature)
        filtered_db = db_interface.get_filtered_by_lng(current_lng)
        filtered_db = filtered_db[(filtered_db['POSITIVES'] != 0)]

        # prepare data
        date_format = date_format_dict[interval]
        filtered_db['TIMESTAMP'] = pd.to_datetime(filtered_db['TIMESTAMP']).dt.strftime(date_format)
        counted_db = filtered_db.groupby(filtered_db['TIMESTAMP'], as_index=False, sort=False).count()
        filtered_db.drop_duplicates(['SIGNATURE'], keep='first', inplace=True)
        filtered_db['LAST_POSITIVES'] = filtered_db['SIGNATURE'].apply(lambda x: db_interface.get_last_positives(x))
        grouped_db = filtered_db.groupby(filtered_db['TIMESTAMP'], as_index=False, sort=False).sum()

        # execute
        self.chart_values = grouped_db['LAST_POSITIVES']
        self.second_chart_values = grouped_db['TOTAL']
        self.formatted_dates = grouped_db['TIMESTAMP']
        self.revision_count = counted_db['TOTAL']
