<h1> README </h1>

<h1>Main Goal</h1>
<p>Provide powerful tool to make learning languages effective, automated and smooth.</p>

<h1>Functionality</h1>
    <p>1. User loads dataset from a csv file. The set is then displayed as cards in random order.  </p>
    <p>2. It's possible to navigate between the cards as well as change the side of the cards (question -> answer).</p>
    <p>3. Subsets of cards from bigger sets can be saved as Revisions for further spaced repetitions</p>
    <p>4. EFC (Ebbinghaus Forgetting Curve) tells the user which sets they should repeat today</p>
    <p>5. User can see stats for currently loaded file</p>
    <p>6. With Score Mode, user will be presented with cards they didn't recognize</p>

<h1>How to install?</h1>
    <p>0. Verify correct instalation of python >= 3.8 </p>
    <p>1. Clone the repository to directory of your choosing</p>
    <p>2. open cmd or powershell from the chosen dir (alt+d and type 'cmd' or 'powershell') and activate following 2 commands:</p>
    <p>     a) python -m venv .\venv</p>
    <p>     b) pip install -r .\scripts\resources\requirements.txt</p>
    <p>3. Create 'revisions' folder in the main dir
    <p>4. You're good!</p>

<h1>Optional Features</h1>
    <p> Add 0 or more from the following codes to config.ini in section 'optional'. Separate with '|'.</p>
    <p>sht_pick - allows user to choose sheet while loading xlsx formats</p>
    <p>switch_lng_rev - adds button to switch between responding revs/lngs</p>
    <p>recommend_new - toogles reccomendations to create a new revision after some specified time</p>
    <p>custom_saveprefix - allows for custom prefixes while saving new revisions</p>