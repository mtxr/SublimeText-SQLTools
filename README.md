![SQLTools](https://github.com/mtxr/SQLTools/raw/images/icon.png?raw=true) SQLTools
===============

[![Join the chat at https://gitter.im/SQLTools/Lobby](https://badges.gitter.im/SQLTools/Lobby.svg)](https://gitter.im/SQLTools/Lobby?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

Your swiss knife SQL for Sublime Text.

Write your SQL with smart completions and handy table and function definitions, execute SQL and explain queries, format your queries and save them in history.

Project website: [https://code.mteixeira.dev/SublimeText-SQLTools/](https://code.mteixeira.dev/SublimeText-SQLTools/)

> If you are looking for VSCode version go to [https://github.com/mtxr/vscode-sqltools](https://github.com/mtxr/vscode-sqltools).

## Donate

SQLTools was developed with ♥ to save us time during our programming journey. But It also takes me time and efforts to develop SQLTools.

SQLTools will save you (for sure) a lot of time and help you to increase your productivity so, I hope you can donate and help SQLTools to become more awesome than ever.

<a href="https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=RSMB6DGK238V8" title="Donate to this project using Paypal"><img src="https://img.shields.io/badge/paypal-donate-yellow.svg" alt="PayPal donate button" /></a>

## Features

* Works with PostgreSQL, MySQL, Oracle, MSSQL, SQLite, Vertica, Firebird and Snowflake
* Smart completions (except SQLite)
* Run SQL Queries &nbsp; <kbd>CTRL+e</kbd>, <kbd>CTRL+e</kbd>
![Auto complete and run SQL queries](https://github.com/mtxr/SQLTools/raw/images/execute_auto_complete.gif?raw=true)
* View table description &nbsp; <kbd>CTRL+e</kbd>, <kbd>CTRL+d</kbd>
![View table schemas](https://github.com/mtxr/SQLTools/raw/images/table_description.gif?raw=true)
* Show table records &nbsp; <kbd>CTRL+e</kbd>, <kbd>CTRL+s</kbd>
![Show table records](https://github.com/mtxr/SQLTools/raw/images/table_records.gif?raw=true)
* Show explain plan for queries &nbsp; <kbd>CTRL+e</kbd>, <kbd>CTRL+x</kbd>
* Formatting SQL Queries &nbsp; <kbd>CTRL+e</kbd>, <kbd>CTRL+b</kbd>
![Formatting SQL Queries](https://github.com/mtxr/SQLTools/raw/images/format_sql.gif?raw=true)
* View Queries history &nbsp; <kbd>CTRL+e</kbd>, <kbd>CTRL+h</kbd>
* Save queries &nbsp; <kbd>CTRL+e</kbd>, <kbd>CTRL+q</kbd>
* List and Run saved queries &nbsp; <kbd>CTRL+e</kbd>, <kbd>CTRL+l</kbd>
* Remove saved queries &nbsp; <kbd>CTRL+e</kbd>, <kbd>CTRL+r</kbd>
* Threading support to prevent lockups
* Query timeout (kill thread if query takes too long)

## Installing

### Using Sublime Package Control

If you are using [Sublime Package Control](https://packagecontrol.io/packages/SQLTools), you can easily install SQLTools via the `Package Control: Install Package` menu item.

1. Press <kbd>CTRL+SHIFT+p</kbd>
2. Type *`Install Package`*
3. Find *`SQLTools`*
4. Wait & Done!

### Download Manually

I strongly recommend you to use Package Control. It helps you to keep the package updated with the last version.

1. Download the latest released zip file [here](https://github.com/mtxr/SublimeText-SQLTools/releases/latest)
2. Unzip the files and rename the folder to `SQLTools`
3. Find your `Packages` directory using the menu item  `Preferences -> Browse Packages...`
4. Copy the folder into your Sublime Text `Packages` directory

### Using SQLTools with Mac OS X

Sublime Text has it's environment variable `PATH` set from launchctl, not by your shell. Binaries installed by packages such as homebrew, for instance `psql` DB CLI for `PostgreSQL`, cannot be found by Sublime Text and results in error in Sublime Text console by `SQLTools`. Installing the package `Fix Mac Path` or setting the full path to your DB CLI binary in `SQLTools.sublime-settings` resolves this issue. Package can be downloaded via [PackageControl](https://packagecontrol.io/packages/Fix%20Mac%20Path) or [github](https://github.com/int3h/SublimeFixMacPath).

## Contributors

This project exists thanks to all the people who [contribute](https://github.com/mtxr/SublimeText-SQLTools/graphs/contributors).


## Configuration 

Documentation: [https://code.mteixeira.dev/SublimeText-SQLTools/](https://code.mteixeira.dev/SublimeText-SQLTools/)




