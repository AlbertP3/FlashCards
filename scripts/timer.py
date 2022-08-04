from PyQt5.QtCore import QTimer
from utils import *



class rev_timer:

    def __init__(self):
        pass


    def initiate_timer(self):
        self.seconds_spent = 0
        self.TIMER_RUNNING_FLAG = False
        self.timer=QTimer()
        self.timer.timeout.connect(self.append_seconds_spent)


    def start_timer(self):
        if not self.TIMER_KILLED_FLAG:
            self.timer.start(1000)
            self.TIMER_RUNNING_FLAG = True
    

    def resume_timer(self):
        if self.conditions_to_resume_timer_are_met():
            self.start_timer()


    def conditions_to_resume_timer_are_met(self):
        if self.seconds_spent != 0 \
            and self.is_saved is False \
            and self.side_window_id is None \
            and not self.TIMER_KILLED_FLAG:
            conditions_met = True
        else:
            conditions_met = False
        return conditions_met


    def stop_timer(self):
        self.timer.stop()
        self.TIMER_RUNNING_FLAG = False
        if not self.do_show_timer:
            self.timer_button.setText('⏹')


    def reset_timer(self, clear_indicator=True):
        self.timer.stop()
        self.seconds_spent = 0
        self.TIMER_RUNNING_FLAG = False
        if clear_indicator:
            self.timer_button.setText('⏲')


    def kill_timer(self):
        self.stop_timer()
        self.TIMER_KILLED_FLAG = True
   

    def append_seconds_spent(self):
        self.seconds_spent+=1
        if self.do_show_timer:
            interval = 'minute' if self.seconds_spent < 3600 else 'hour'
            self.timer_button.setText(format_seconds_to(self.seconds_spent, interval))
        else:
            self.timer_button.setText('⏲')


    def get_seconds_spent(self):
        return self.seconds_spent

