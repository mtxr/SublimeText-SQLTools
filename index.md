![SQLTools](https://github.com/mtxr/SQLTools/raw/images/icon.png?raw=true) SQLTools
===============

Your swiss knife SQL for Sublime Text.

Write your SQL with smart completions and hady table and function definitions, execute SQL and explain queries, format your queries and save them in history.

Project website: [http://mtxr.github.io/SQLTools/](http://mtxr.github.io/SQLTools/)

## Donate

SQLTools was developed with ♥ to save us time during our programming journey. But It also takes me time and efforts to develop SQLTools.

SQLTools will save you (for sure) a lot of time and help you to increase your productivity so, I hope you can donate and help SQLTools to become more awesome than ever.

<span class="badge-paypal"><a href="https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=RSMB6DGK238V8" title="Donate to this project using Paypal"><img src="https://img.shields.io/badge/paypal-donate-yellow.svg" alt="PayPal donate button" /></a></span>

## Features

* Smart auto completions (for PostgreSQL, MySQL, Oracle, MSSQL, Vertica, Firebird)
* Run SQL Queries (`CTRL+e, CTRL+e`)
![Auto complete (PostgreSQL & MySQL) && Run SQL Queries](https://github.com/mtxr/SQLTools/raw/images/execute_auto_complete.gif?raw=true)
* View table schemas (`CTRL+e, CTRL+d`)
![View table schemas](https://github.com/mtxr/SQLTools/raw/images/table_description.gif?raw=true)
* View Queries history (`CTRL+e, CTRL+h`)
* Show table records (`CTRL+e, CTRL+s`)
![Show table records](https://github.com/mtxr/SQLTools/raw/images/table_records.gif?raw=true)
* Show explain plan for queries (PostgreSQL, MySQL, Oracle, Vertica, SQLite) (`CTRL+e, CTRL+x`)
* Formatting SQL Queries (`CTRL+e, CTRL+b`)
![Formatting SQL Queries](https://github.com/mtxr/SQLTools/raw/images/format_sql.gif?raw=true)
* Threading Support (prevent ST lockups)
* Query timeout (Kill thread if query takes too long)
* Unescape chars for languages (PHP \" is replace by ")
* Save queries (`CTRL+e, CTRL+q`)
* List and Run saved queries (`CTRL+e, CTRL+a`)
* Remove saved queries (`CTRL+e, CTRL+r`)

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


## Settings

| Option                  | Description                                                                                                      | Type      | Default value     |
| ---                     | :---                                                                                                             | ---       | ---               |
| `unescape_quotes`       | Escape chars like \\" and \\' for extension in array                                                             | `array`   | `[ "php" ]`       |
| `cli`                   | Path to desired command. You can check more on [Path to Cli](#path-to-commands)                                  | `object`  |                   |
| `thread_timeout`        | Query execution time in miliseconds before kill. Prevents Sublime Text from lockup while running complex queries | `int`     | 15                |
| `use_streams`        | Stream results to output | `boolean`     | `false`                |
| `show_result_on_window` | Show query result using a window (true) or a panel (false)                                                       | `boolean` | `false`           |
| `show_records`          | Resultset settings. You can check more on [Show records options](#show-records-options)                          | `object`  | `{"limit": 50}`   |
| `format`                | SQL formatting settings. You can check more on [SQL Formatting](#sql-formatting)                                 | `object`  |                   |
| `safe_limit`            | Optionally set a default LIMIT on queries.  Parameter can be an INT or false.                                    | `int`     | `false`           |
| `show_query`            | Optionally show the executed query above the results.                                                            | `boolean` | `false`           |
| `expand_to_paragraph`   | Expand cursor selection to current paragraph upon running an SQL query.                                          | `boolean` | `false`           |

### <a id="show-records-options"></a>Show records options

| Option  | Description                                                 | Type  | Default value |
| ---     | :---                                                        | ---   | ---           |
| `limit` | number of rows to show whe using Show Table Records command | `int` | 50            |


### <a id="sql-formatting"></a>SQL Formatting

| Option            | Description                                                                                                                           | Type      | Default value |
| ---               | :---                                                                                                                                  | ---       | ---           |
| `keyword_case`    | Changes how keywords are formatted. Allowed values are `"upper"`, `"lower"` and `"capitalize"` and `null` (leaves case intact)  | `string`  | `"upper"`   |
| `identifier_case` | Changes how identifiers are formatted. Allowed values are `"upper"` `"lower"` and `"capitalize"`and `null` (leaves case intact) | `string`  | `null`        |
| `strip_comments`  | Remove comments from file/selection                                                                                                   | `boolean` | `false`       |
| `indent_tabs`     | Use tabs instead of spaces                                                                                                            | `boolean` | `false`       |
| `indent_width`    | Indentation width                                                                                                                     | `int`     | 4             |
| `reindent`        | Reindent code if `true`                                                                                                               | `boolean` | `true`        |

### <a id="path-to-commands"></a>Path to Cli

In case your database command is not in your `PATH` enviroment var, you can set the path here.

| Option       | Default value |
| ---          | ---           |
| `"mysql"`    | `"mysql"`     | 
| `"pgsql"`    | `"psql"`      |
| `"oracle"`   | `"sqlplus"`   |
| `"vertica"`  | `"vsql"`      |
| `"sqsh" `    | `"sqsh"`      |
| `"firebird"` | `"isql"`      |
| `"sqlite"`   | `"sqlite3"`   |

## Connections

You can setup your connecitons using the `Preferences` menu or `CTRL+SHIFT+P` and searching for `ST: Setup Connections`. 

Below you can see an example of the `SQLToolsConnections.sublime-settings`:

```json
{
    "connections": {
        "Connection MySQL": {
            "type"    : "mysql",
            "host"    : "127.0.0.1",
            "port"    : 3306,
            "database": "dbname",
            "username": "user",
            "password": "password",  // you will get a security warning in the output
            // "defaults-extra-file": "/path/to/defaults_file_with_password",  // use [client] or [mysql] section
            // "login-path": "your_login_path",  // login path in your ".mylogin.cnf"
            "encoding": "utf-8"
        },
        "Connection PostgreSQL": {
            "type"    : "pgsql",
            "host"    : "127.0.0.1",
            "port"    :  5432,
            "database": "dbname",
            "username": "anotheruser",
            // for PostgreSQL "password" is optional (setup "pgpass.conf" file instead)
            "password": "password",
            "encoding": "utf-8"
        },
        "Connection Oracle": {
            "type"    : "oracle",
            "host"    : "127.0.0.1",
            "port"    :  1522,
            "database": "dbname",
            "username": "anotheruser",
            "password": "password",
            "service" : "servicename",
            "encoding": "utf-8"
        },
        "Connection SQLite": {
            "type"    : "sqlite",
            "database": "d:/sqlite/sample_db/chinook.db",
            "encoding": "utf-8"
        }
    },
    "default": "Connection MySQL"
}
```

You can also add connections to your `.sublime-project` files to use per-project connections.

## Auto Complete

After you select one connection, SQLTools will prepare auto completions for you.

PS: For a better experience, add this line to your sublime settings file

1. `CTRL+SHIFT+p`, select "*Preferences: Settings - User*"
2. add this option: 


```json
{
  "auto_complete_triggers": [
    {"selector": "text.html", "characters": "<" },
    {"selector": "source.sql", "characters": "."}
  ]
}
```

## Using SQLTools with Mac OS X

Sublime Text has it's evironment variable `PATH` set from launchctl, not by your shell. Binaries installed by packages such as homebrew, for instance `psql` DB CLI for `PostgreSQL`, cannot be found by Sublime Text and results in error in Sublime Text console by `SQLTools`. Installing the package `Fix Mac Path` or setting the full path to your DB CLI binary in `SQLTools.sublime-settings` resolves this issue. Package can be downloaded via [PackageControl](https://packagecontrol.io/packages/Fix%20Mac%20Path) or [github](https://github.com/int3h/SublimeFixMacPath).
