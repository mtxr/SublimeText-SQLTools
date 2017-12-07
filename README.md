![SQLTools v0.5.4](https://github.com/mtxr/SQLTools/raw/images/icon.png?raw=true) SQLTools
===============

<span class="badge-paypal"><a href="https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=RSMB6DGK238V8" title="Donate to this project using Paypal"><img src="https://img.shields.io/badge/paypal-donate-yellow.svg" alt="PayPal donate button" /></a></span>

Your swiss knife SQL for Sublime Text.

> If you are looking for VSCode version go to [https://github.com/mtxr/vscode-sqltools](https://github.com/mtxr/vscode-sqltools).

Write your SQL with smart completions and hady table and function definitions, execute SQL and explain queries, format your queries and save them in history.

Project website: [http://mtxr.github.io/SQLTools/](http://mtxr.github.io/SQLTools/)

## Donate

SQLTools was developed with ♥ to save us time during our programming journey. But It also takes me time and efforts to develop SQLTools.

SQLTools will save you (for sure) a lot of time and help you to increase your productivity so, I hope you can donate and help SQLTools to become more awesome than ever.

<span class="badge-paypal"><a href="https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=RSMB6DGK238V8" title="Donate to this project using Paypal"><img src="https://img.shields.io/badge/paypal-donate-yellow.svg" alt="PayPal donate button" /></a></span>



## Contributors

These fellows helped SQLTools become better than ever. Thank you so much!

* [@tkopets](https://github.com/tkopets)
* [@gabrielebarbieri](https://github.com/gabrielebarbieri)

## Features

* Smart auto completions (for PostgreSQL, MySQL, Oracle, MSSQL, Vertica, Firebird)
* Run SQL Queries (<kbd>CTRL+e</kbd>, <kbd>CTRL+e</kbd>)
![Auto complete (PostgreSQL & MySQL) && Run SQL Queries](https://github.com/mtxr/SQLTools/raw/images/execute_auto_complete.gif?raw=true)
* View table schemas (<kbd>CTRL+e</kbd>, <kbd>CTRL+d</kbd>)
![View table schemas](https://github.com/mtxr/SQLTools/raw/images/table_description.gif?raw=true)
* View Queries history (<kbd>CTRL+e</kbd>, <kbd>CTRL+h</kbd>)
* Show table records (<kbd>CTRL+e</kbd>, <kbd>CTRL+s</kbd>)
![Show table records](https://github.com/mtxr/SQLTools/raw/images/table_records.gif?raw=true)
* Show explain plan for queries (PostgreSQL, MySQL, Oracle, Vertica, SQLite) (<kbd>CTRL+e</kbd>, <kbd>CTRL+x</kbd>)
* Formatting SQL Queries (<kbd>CTRL+e</kbd>, <kbd>CTRL+b</kbd>)
![Formatting SQL Queries](https://github.com/mtxr/SQLTools/raw/images/format_sql.gif?raw=true)
* Threading Support (prevent ST lockups)
* Query timeout (Kill thread if query takes too long)
* Unescape chars for languages (PHP \" is replace by ")
* Save queries (<kbd>CTRL+e</kbd>, <kbd>CTRL+q</kbd>)
* List and Run saved queries (<kbd>CTRL+e</kbd>, <kbd>CTRL+a</kbd>)
* Remove saved queries (<kbd>CTRL+e</kbd>, <kbd>CTRL+r</kbd>)

## Installing

### Using Sublime Package Control

If you are using [Sublime Package Control](http://wbond.net/sublime_packages/package_control), you can easily install SQLTools via the `Package Control: Install Package` menu item.

1. Press `CTRL+SHIFT+p`
2. Type *"Install Package"* 
3. Find SQLTools
4. Wait & Done!

### Download Manually

I strongly recomend you to use Package Control. It helps you to keep the package updated with the last version.

1. Download the files zip file [here](http://mtxr.github.io/SQLTools/)
2. Unzip the files and rename the folder to `SQLTools`
3. Find your `Packages` directory using the menu item  `Preferences -> Browse Packages...`
4. Copy the folder into your Sublime Text `Packages` directory

### Using SQLTools with Mac OS X

Sublime Text has it's evironment variable `PATH` set from launchctl, not by your shell. Binaries installed by packages such as homebrew, for instance `psql` DB CLI for `PostgreSQL`, cannot be found by Sublime Text and results in error in Sublime Text console by `SQLTools`. Installing the package `Fix Mac Path` or setting the full path to your DB CLI binary in `SQLTools.sublime-settings` resolves this issue. Package can be downloaded via [PackageControl](https://packagecontrol.io/packages/Fix%20Mac%20Path) or [github](https://github.com/int3h/SublimeFixMacPath).

## Configuration 

Documentation: [http://mtxr.github.io/SQLTools/](http://mtxr.github.io/SQLTools/)
