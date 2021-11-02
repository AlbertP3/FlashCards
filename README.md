<h1> README </h1>

<h1>Main Goal</h1>
Provide powerful tool to make learning languages effective, automated and smooth.


<h1>Functionality</h1>
    1. Application allows user to load {datasets} from csv or xlsx files. The set is then displayed word-by-word in random order.  
    2. User can navigate between words as well as change the side of the cards (question -> answer).  
    3. EFC tells user which sets they should repeat today (by filename)  
    4. User can see information about currently loaded file (from db, by filename)  
    5. With Score Mode, user will be presented with the % score after revision ends  


<h1>Graphical User Interface</h1>
    1. gui_main - console for showing words and all buttons - central point of the app
    2. gui_load_lngs - dialog enabling user to pick up languages & revisions
    3. gui_efc - show remainig # of repetitions according to the Ebbinghaus Forgetting Curve
    4. gui_ctrl_panel - shows info about currently displayed lng or rev

<h1>Logic</h1>
    1. backend - background processes (deeper than nav_logic)
    2. nav_logic - handles moving around the interface
    3. efc - logic of the Ebbinghaus Forgetting Curve
    4. db_api - interactions with the Database comprising repetitions records
    5. utils - versatile, reusable functions that come in handy just when you need them
