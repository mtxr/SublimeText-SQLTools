![SQLTools](https://github.com/mtxr/SQLTools/raw/images/icon.png?raw=true) SQLTools
===============

Your swiss knife SQL for Sublime Text.

Project website: [http://mtxr.github.io/SQLTools/](http://mtxr.github.io/SQLTools/)

## Donate

SQLTools was developed with ♥ to save us time during our programming journey. But It also takes me time and efforts to develop SQLTools.

SQLTools will save you (for sure) a lot of time and help you to increase your productivity so, I hope you can donate and help SQLTools to become more awesome than ever.

<span class="badge-paypal"><a href="https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=RSMB6DGK238V8" title="Donate to this project using Paypal"><img src="https://img.shields.io/badge/paypal-donate-yellow.svg" alt="PayPal donate button" /></a></span>

## Features

* View table schemas (`CTRL+e, CTRL+d`)
![View table schemas](https://github.com/mtxr/SQLTools/raw/images/table_description.gif?raw=true)
* View Queries history (`CTRL+e, CTRL+h`)
* Show table records (`CTRL+e, CTRL+s`)
![Show table records](https://github.com/mtxr/SQLTools/raw/images/table_records.gif?raw=true)
* Auto complete (for PostgreSQL & MySQL. Looking for help with other SGDBs)
* Run SQL Queries (`CTRL+e, CTRL+e`)
![Auto complete (PostgreSQL & MySQL) && Run SQL Queries](https://github.com/mtxr/SQLTools/raw/images/execute_auto_complete.gif?raw=true)
* Formatting SQL Queries (`CTRL+e, CTRL+b`)
![Formatting SQL Queries](https://github.com/mtxr/SQLTools/raw/images/format_sql.gif?raw=true)
* Threading Support (prevent ST lockups)
* Query timeout (Kill thread if query takes too long)
* Unescape chars for languages (PHP \" is replace by ")
* Save queries (`CTRL+e, CTRL+q`)
* List and Run saved queries (`CTRL+e, CTRL+a`)
* Remove saved queries (`CTRL+e, CTRL+r`)

## Todo

Up coming features:
- [ ] Auto complete for Oracle, Vertica, Firebird and SQLite

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
| `unescape_quotes`       | Escape chars like \\" and \\' for extension in array                                                            | `array`   | `[ "php" ]`     |
| `cli`                   | Path to desired command. You can check more on [Path to Cli](#path-to-commands)                                  | `object`  |                   |
| `thread_timeout`        | Query execution time in miliseconds before kill. Prevents Sublime Text from lockup while running complex queries | `int`     | 5000              |
| `show_result_on_window` | Show query result using a window (true) or a panel (false)                                                       | `boolean` | `false`           |
| `show_records`          | Resultset settings. You can check more on [Show records options](#show-records-options)                          | `object`  | `{"limit": 50}` |
| `format`                | SQL formatting settings. You can check more on [SQL Formatting](#sql-formatting)                                 | `object`  | `{"limit": 50}` |

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

SQLToolConnections.sublime-settings example:

```json
{
    "connections": {
        "Connection 1": {
            "type"    : "mysql",
            "host"    : "127.0.0.1",
            "port"    : 3306,
            "username": "user",
            "password": "password",
            "database": "dbname",
            "encoding": "utf-8"
        },
        "Connection 2": {
            "type"    : "pgsql",
            "host"    : "127.0.0.1",
            "port"    :  5432,
            "username": "anotheruser",
            "database": "dbname",
            "encoding": "utf-8"
        },
        "Connection 3": {
            "type"    : "oracle",
            "host"    : "127.0.0.1",
            "port"    :  1522,
            "username": "anotheruser",
            "password": "password",
            "database": "dbname",
            "service" : "servicename",
            "encoding": "utf-8"
        }
    },
    "default": "Connection 1"
}
```


## Auto Complete

After you select one connection, SQLTools prepare auto completions for you.

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
