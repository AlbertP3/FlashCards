import gui_main


# Module contains Flashcards Console Commands
# Functions only return values w/o implicitly printing to console

class fcc():

    def __init__(self, subject=None):
        self.subject = subject
        self.DOCS = {'modify_card':['main_window','Allows rewriting for current side of the card. Changes will be written to the rev file'],
                    'modify_score':['main_window','Asks for new value pos/neg for currently displayed card']}


    def init(self):
        user_input = input('Enter a command: ')
        return self.invoke_command(user_input)


    def invoke_command(self, command: str):
        command = command.lower()
        parsed_cmd = self.parse_input(command)
        try:
            function_to_call = getattr(self, parsed_cmd[0])
            output = function_to_call(parsed_cmd)
        except:
            output = 'Invalid Command'
        return output


    def parse_input(self, input):
        # returns a list = [func_name, arg1, arg2,...]
        return input.split(' ')


    def verify_permission(self, parsed_cmd):
        # if parsed_cmd
        pass


    def help(self, parsed_cmd):
        if len(parsed_cmd) > 1:
            function = parsed_cmd[1]
            return self.DOCS[function][1]
        else:
            return([desc[1] for desc in self.DOCS.items()])
    

    def modify_card(self, parsed_cmd):
        # check preconditions
        if not isinstance(self.subject, gui_main.main_window_logic): 
            return 'Main Window object is required.'
        if len(parsed_cmd) < 2: 
            return 'modify_card requires at least 1 word'    

        new_text = ' '.join(parsed_cmd[1:])
        filepath = self.subject.get_filepath()        


    def modify_score(self):
        pass

