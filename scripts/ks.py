# this module should stay minimal as it is imported with a '*'
from utils import Config
config = Config()

if 'vim_ks' in config['optional']:
    kss = dict(
         next = 'l',
         prev = 'h',
         negative = 'j',
         reverse = 'k',
         change_revmode = 'x',
         del_cur_card = 'd',
         load_again = 'r',
         timespent = 't',
         progress = 'p',
         config = 'q',
         fcc = 'c',
         run_command = 'Insert',
         efc = 'e',
         load = 'w',
         mistakes = 'm',
         stats = 's',
     )
elif 'keyboard_shortcuts' in config['optional']:
    kss = dict(
         next = 'right',
         prev = 'left',
         negative = 'down',
         reverse = 'up',
         change_revmode = 'p',
         del_cur_card = 'd',
         load_again = 'r',
         timespent = 't',
         progress = 'h',
         config = 'q',
         fcc = 'c',
         run_command = 'Insert',
         efc = 'e',
         load = 'l',
         mistakes = 'm',
         stats = 's',
    )
else:
    kss = dict(
        next = '',
        prev = '',
        negative = '',
        reverse = '',
        change_revmode = '',
        del_cur_card = '',
        load_again = '',
        timespent = '',
        progress = '',
        config = '',
        fcc = 'c',
        run_command = 'Insert',
        efc = '',
        load = '',
        mistakes = '',
        stats = '',
    )

