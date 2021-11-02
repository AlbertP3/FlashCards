<h1> README </h1>

<h1>Main Goal</h1>
<p>Provide powerful tool to make learning languages effective, automated and smooth.</p>

<h1>Functionality</h1>
    <p>1. Application allows user to load {datasets} from csv or xlsx files. The set is then displayed word-by-word in </p><p>random order.  </p>
    <p>2. User can navigate between words as well as change the side of the cards (question -> answer).  </p>
    <p>3. EFC tells user which sets they should repeat today (by filename)  </p>
    <p>4. User can see information about currently loaded file (from db, by filename)  </p>
    <p>5. With Score Mode, user will be presented with the % score after revision ends  </p>


<h1>Graphical User Interface</h1>
    <p>1. gui_main - console for showing words and all buttons - central point of the app</p>
    <p>2. gui_load_lngs - dialog enabling user to pick up languages & revisions</p>
    <p>3. gui_efc - show remainig # of repetitions according to the Ebbinghaus Forgetting Curve</p>
    <p>4. gui_ctrl_panel - shows info about currently displayed lng or rev</p>

<h1>Logic</h1>
    <p>1. backend - background processes (deeper than nav_logic)</p>
    <p>2. nav_logic - handles moving around the interface</p>
    <p>3. efc - logic of the Ebbinghaus Forgetting Curve</p>
    <p>4. db_api - interactions with the Database comprising repetitions records</p>
    <p>5. utils - versatile, reusable functions that come in handy just when you need them</p>
