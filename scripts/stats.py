from utils import *
import db_api



class stats():

    def __init__(self):
        self.config = load_config()

    
    def get_data(self):
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
