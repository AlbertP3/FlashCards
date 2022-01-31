from PyQt5.QtCore import pyqtRemoveInputHook
from utils import *



class fcc():
    # Flashcards console commands allows access to extra functionality
    # through the console. To be used exclusively with an object of type
    # main_window_logic. Behaviour of certain function might adjust if
    # graphical interface is available.

    def __init__(self):
        self.TEMP_FILE_FLAG = False
        self.DOCS = {'mct':'Modify Cards Text - edits current side of the card both in current set and in the original file',
                        'mcr':'Modify Card Result - allows changing pos/neg for the current card. Add "+" or "-" arg to specify target result',
                        'dc':'Delete Card - deletes card both in current set and in the file',
                        'lln':'Load Last N, loads N-number of words from the original file, starting from the end',
                        'cfm':'Create Flashcards from Mistakes List - initiate new set from current mistakes'}


    def init_command_prompt(self):
        pyqtRemoveInputHook()
        # allows user to enter commands from the console
        user_input = input('Enter a command: ')
        parsed_input = user_input.split(' ')
        if self.is_allowed_command(parsed_input[0]):
            function_to_call = getattr(self, parsed_input[0])
            function_to_call(parsed_input)
        else:
            print('Permision Denied or Unknown Command. Type help for... well - help')


    def is_allowed_command(self, command):
        return command in ['mct', 'mcr', 'dc', 'lln', 'help', 'cfm']
    

    def reset_temp_file_flag(self):
        self.TEMP_FILE_FLAG = False


    def refresh_interface(self):
        # try refresh interface if available
        try:
            self.update_interface_parameters()
        except:
            pass


    def help(self, parsed_cmd):
        if len(parsed_cmd) == 1:
           printout = get_pretty_print(self.DOCS, extra_indent=3)
        else:
            command = parsed_cmd[1]
            printout =  get_pretty_print([[command, self.DOCS[command]]], extra_indent=3)
        print(printout)


    def mct(self, parsed_cmd):
        # Modify current card text - both in app and in file

        # check preconditions
        if len(parsed_cmd) < 2:
            print('mc function require at least 2 arguments')
            return
            
        new_text = ' '.join(parsed_cmd[1:])
        # change text on the card
        self.dataset.iloc[self.current_index, self.side] = new_text

        # change text in the file
        save_success = True
        if self.TEMP_FILE_FLAG == False:
            save_success = save_revision(self.dataset, self.signature)

        if save_success:
            print('Card content successfully modified.')


    def mcr(self, parsed_cmd):
        # Modify Card Result - allows modification of current score

        # check preconditions
        if len(parsed_cmd) != 2:
            print('mcr function require 2 arguments. "+" and "-" are accepted.')
            return

        mistakes_one_side = [x[1-self.side] for x in self.mistakes_list]
        is_mistake = self.get_current_card()[self.side] in mistakes_one_side

        if parsed_cmd[1] == '+' and is_mistake:
            mistake_index = mistakes_one_side.index(self.get_current_card()[self.side])
            del self.mistakes_list[mistake_index]
            self.positives+=1
            self.negatives-=1
        elif parsed_cmd[1] == '-' and not is_mistake:
            self.positives-=1
            self.result_negative()
        else:
            print('Wrong argument entered.')

        self.refresh_interface()

        print('Score successfully modified.')


    def dc(self, parsed_cmd):
        # Delete card - from set and from the file

        # check preconditions
        if len(parsed_cmd) != 2:
            print('Wrong number of args. Expected 2.')
            return
        elif parsed_cmd[1] != '-':
            print('Wrong confirmation sign. Expected "-".')
            return

        # Get parameters before deletion
        current_side = self.get_current_side()
        current_word = self.get_current_card()[current_side]

        # Delete from currently loaded set
        self.delete_current_card()

        # Delete from the file - load file again to maintain original order
        save_success = True
        if self.TEMP_FILE_FLAG == False:
            dataset_ordered = load_dataset(self.get_filepath(), do_shuffle=False)
            dataset_ordered.drop(dataset_ordered.loc[dataset_ordered[dataset_ordered.columns[current_side]]==current_word].index, inplace=True)
            save_success = save_revision(dataset_ordered, self.signature)

        if save_success:
            print('Card deleted successfully.')


    def lln(self, parsed_cmd):
        # load last N cards from dataset

        # check preconditions
        if len(parsed_cmd) != 2:
            print('Expected 2 args.')
            return
        elif not parsed_cmd[1].isnumeric():
            print('number of cards must be a number')
            return
        
        # get last N records from the file -> shuffle only the part
        n_cards = abs(int(parsed_cmd[1]))
        file_path = self.get_filepath()
        data = load_dataset(file_path, do_shuffle=False).iloc[-n_cards:, :]
        data = data.sample(frac=1).reset_index(drop=True)

        # point to non-existing file in case user modified cards
        filename = file_path.split('/')[-1].split('.')[0]
        new_path = self.config['lngs_path'] + filename + str(n_cards) + '.csv'
        
        self.update_backend_parameters(new_path, data)
        self.refresh_interface()
        self.TEMP_FILE_FLAG = True

        print(f'Loaded last {n_cards} cards.')

    
    def cfm(self, parsed_cmd):
        # Create Flashcards from Mistakes list
        
        # Create DataFrame
        mistakes_list = pd.DataFrame(self.get_mistakes_list(), columns=self.get_headings())
                                            
        # point to a fictional LNG file as to allow save as a new revision
        fict_path = self.config['lngs_path'] + 'mistakes_list.csv'

        self.update_backend_parameters(fict_path, mistakes_list)
        self.refresh_interface()

        self.TEMP_FILE_FLAG = True
        # allow instant save of a rev created from mistakes_list
        self.set_cards_seen(mistakes_list.shape[0]-1)
        
        print('Successfully created flashcards from mistakes list.')
        