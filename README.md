<h1> FLASHCARDS </h1>

![Flashcards Main Window](scripts/resources/readme_img_1.png)

<h1>Main Goal</h1>
<p>Provide powerful tool to make learning languages effective, automated and smooth.</p>

<h1>About</h1>
<ol>
<li>Allows loading datasets into a form of cards. Order is always randomized.</li>
<li>User is free to create their own datasets as long as they comply with the specific format (2 columns + headers). Example file is included in the distributed version of the app</li>
<li>In app, file is picked via a convenient side-window opened with a dedicated button. Only revisions and languages folders are searched.</li>
<li>It's possible to navigate between the cards as well as to change the side of the cards (question -> answer)</li>
<li>Subsets of cards from bigger sets can be saved as Revisions for further spaced repetitions</li>
<li>Spaced repetitons are reinforced by employing EFC (Ebbinghaus Forgetting Curve) that tells the user which sets they should repeat today</li>
<li>Revisions can be appraised - score is then recorded to the Database</li>
<li>In a revision mode, user can open a mistakes list side-window to see which cards they guessed wrong. Available with 'm' or score button.</li>
<li>User is also able to see statistics regarding currently loaded file</li>
<li>With Flashcards Console Commands user is able to access some extra functionalities listed in README file that are also available via 'help' command directly in the console</li>
</ol>

<h1>Tech Stack</h1>
<p>Application was built with Python 3.8. Following libraries were employed:</p>
<ol>
<li><b>pandas</b> - loading and manipulating files</li>
<li><b>numpy</b> - dependency for pandas</li>
<li><b>PyQt5</b> - Graphical User Interface</li>
<li><b>matplotlib</b> - statistics visualization</li>
</ol>

<h1>How to install?</h1>
    <ol>
        <li><b>For distributed application</b>: download archive from the provided link, unpack wherever convenient and keep all the files in one folder. </li>
        <li><b>For repository</b>:  clone repository, setup venv and install all libraries from requirements.txt. Please note that in order to run vbs launcher (allows running app without a console), absolute path mustn't contain spaces</li>
    </ol>

<h1>Keyboard Shortcuts</h1>
    <ol>
        <li><b>RIGHT</b>  -   navigate to the next card. If revision mode is on: also mark positive result </li>
        <li><b>LEFT</b>   -   navigate to the previous card</li>
        <li><b>UP</b>     -   reverse side of the currently displayed card</li>
        <li><b>DOWN</b>   -   in revision mode only - mark negative result and go to next card</li>
        <li><b>p</b>      -   change revision mode</li>
        <li><b>l</b>      -   open load side-window with all files stored in revisions and languages dirs</li>
        <li><b>e</b>      -   open efc side-window with reccommended revisions</li>
        <li><b>s</b>      -   open stats side-window with statistics concerning currently loaded revision</li>
        <li><b>c</b>      -   open console side-window allowing user to access the Flashcards Console Commands</li>
        <li><b>d</b>      -   delete currently displayed card. Does not modify the file itself</li>
        <li><b>m</b>      -   open mistakes side-window displaying all the cards user guessed wrong</li>
        <li><b>r</b>      -   reload the currently loaded file</li>
        <li><b>esc</b>    -   close curretnly opened side-window</li>
    </ol>

<h1>Console Commands</h1>
All the commands are run via in-build console opened by pressing the 'c' key. Press INSERT to run the command.
    <ol>
        <li><b>help</b>    -   Says what it does - literally</li>
        <li><b>mct</b>     -   Modify Cards Text - edits current side of the card both in current set and in the original file</li>
        <li><b>mcr</b>     -   Modify Card Result - allows changing pos/neg for the current card. Add "+" or "-" arg to specify target result</li>
        <li><b>dc</b>      -   Delete Card - deletes card both in current set and in the file</li>
        <li><b>lln</b>     -   Load Last N, loads N-number of words from the original file, starting from the end</li>
        <li><b>cfm</b>     -   Create Flashcards from Mistakes List - initiate new set from current mistakes and by default append to mistakes_list file</li>
        <li><b>efc</b>     -   Ebbinghaus Forgetting Curve - shows table with revs, days from last rev and efc score</li>
        <li><b>mcp</b>     -   Modify Config Parameter - allows modifications of config file</li>
        <li><b>sck</b>     -   Show Config Keys - list all available parameters in config file</li>
        <li><b>cls</b>     -   Clear Screen</li>
        <li><b>cfn</b>     -   Change File Name - changes currently loaded file_path, filename and all records in DB for this signature</li>
    </ol>

<h1>Optional Features</h1>
    <p> Add 0 or more from the following codes to config.ini in section 'optional'. Separate with '|'.</p>
    <p><b>reccommend_new</b> - toogles reccomendations to create a new revision after some specified time</p>
    <p><b>keyboard_shortcuts</b></p>

<h1>Known Bugs</h1>
<ol>
<li>If absolute path to the launcher (.vbs) contains whitespaces then the app will not launch and launcher.bat is to be recoursed to.</li>
</ol>