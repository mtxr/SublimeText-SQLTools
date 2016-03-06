![SQLTools](https://github.com/mtxr/SQLTools/raw/images/icon.png?raw=true) SQLTools
===============

A swiss knife for SQL in Sublime Text.

## Donate

Donate and help SQLTools to become more awesome than ever.

<span class=\"badge-paypal\"><a href=\"https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=RSMB6DGK238V8\" title=\"Donate to this project using Paypal\"><img src=\"https://img.shields.io/badge/paypal-donate-yellow.svg\" alt=\"PayPal donate button\" /></a></span>

## Features
* View table schemas (`CTRL+e, CTRL+d`)
![View table schemas](https://github.com/mtxr/SQLTools/raw/images/table_description.gif?raw=true)
* View Queries history (`CTRL+e, CTRL+h`)
* Show table records (`CTRL+e, CTRL+s`)
![Show table records](https://github.com/mtxr/SQLTools/raw/images/table_records.gif?raw=true)
* Auto complete (PostgreSQL & MySQL)
* Run SQL Queries (`CTRL+e, CTRL+e`)
![Auto complete (PostgreSQL & MySQL) && Run SQL Queries](https://github.com/mtxr/SQLTools/raw/images/execute_auto_complete.gif?raw=true)
* Formatting SQL Queries (`CTRL+e, CTRL+b`)
![Formatting SQL Queries](https://github.com/mtxr/SQLTools/raw/images/format_sql.gif?raw=true)
* Threading Support (prevent ST lockups)
* Query timeout (Kill thread if query takes too long)
* Unescape chars for languages (PHP \\\" is replace by \")

## Todo

Up coming features:

- [ ] Save queries
- [ ] Get saved queries
- [ ] Run saved queries
- [ ] Auto complete for Oracle and Vertica

## Installing

As long SQLTools is not in the Package Control repository yet (pull request already sent! :D) you can install SQLTools using via sublime in X steps:

1. Press `CTRL+SHIFT+p`
2. Type *\"Add repository\"* 
3. Paste this url https://github.com/mtxr/SQLTools
4. Press `CTRL+SHIFT+p` again
5. Select *\"Install package\"*
6. Select *\"SQLTools\"*
7. Done!

## Settings

| Option                  | Description                                                                                                      | Type      | Default value     |
| ---                     | :---                                                                                                             | ---       | ---               |
| `unescape_quotes`       | Escape chars like \\\" and \\' for extension in array                                                            | `array`   | `[ \"php\" ]`     |
| `cli`                   | Path to desired command. You can check more on [Path to Cli](#path-to-commands)                                  | `object`  |                   |
| `thread_timeout`        | Query execution time in miliseconds before kill. Prevents Sublime Text from lockup while running complex queries | `int`     | 5000              |
| `show_result_on_window` | Show query result using a window (true) or a panel (false)                                                       | `boolean` | `false`           |
| `show_records`          | Resultset settings. You can check more on [Show records options](#show-records-options)                          | `object`  | `{\"limit\": 50}` |
| `format`                | SQL formatting settings. You can check more on [SQL Formatting](#sql-formatting)                                 | `object`  | `{\"limit\": 50}` |

### <a id=\"show-records-options\"></a>Show records options

| Option  | Description                                                 | Type  | Default value |
| ---     | :---                                                        | ---   | ---           |
| `limit` | number of rows to show whe using Show Table Records command | `int` | 50            |


### <a id=\"sql-formatting\"></a>SQL Formatting

| Option            | Description                                                                                                                           | Type      | Default value |
| ---               | :---                                                                                                                                  | ---       | ---           |
| `keyword_case`    | Changes how keywords are formatted. Allowed values are `\"upper\"`, `\"lower\"` and `\"capitalize\"` and `null` (leaves case intact)  | `string`  | `\"upper\"`   |
| `identifier_case` | Changes how identifiers are formatted. Allowed values are `\"upper\"` `\"lower\"` and `\"capitalize\"`and `null` (leaves case intact) | `string`  | `null`        |
| `strip_comments`  | Remove comments from file/selection                                                                                                   | `boolean` | `false`       |
| `indent_tabs`     | Use tabs instead of spaces                                                                                                            | `boolean` | `false`       |
| `indent_width`    | Indentation width                                                                                                                     | `int`     | 4             |
| `reindent`        | Reindent code if `true`                                                                                                               | `boolean` | `true`        |

### <a id=\"path-to-commands\"></a>Path to Cli

In case your database command is not in your `PATH` enviroment var, you can set the path here.

| Option    | Default value |
| ---       | ---           |
| `mysql`   | `\"mysql\"`   |
| `pgsql`   | `\"psql\"`    |
| `oracle`  | `\"sqlplus\"` |
| `vertica` | `\"vsql\"`    |

## Connections

SQLToolConnections.sublime-settings example:

```json
{
    \"connections\": {
        \"Connection 1\": {
            \"type\"    : \"mysql\",
            \"host\"    : \"127.0.0.1\",
            \"port\"    : 3306,
            \"username\": \"user\",
            \"password\": \"password\",
            \"database\": \"dbname\"
        },
        \"Connection 2\": {
            \"type\"    : \"pgsql\",
            \"host\"    : \"127.0.0.1\",
            \"port\"    :  5432,
            \"username\": \"anotheruser\",
            \"database\": \"dbname\"
        },
        \"Connection 3\": {
            \"type\"    : \"oracle\",
            \"host\"    : \"127.0.0.1\",
            \"port\"    :  1522,
            \"username\": \"anotheruser\",
            \"password\": \"password\",
            \"database\": \"dbname\",
            \"service\" : \"servicename\"
        }
    },
    \"default\": \"Connection 1\"
}
```


## Auto Complete

After you select one connection, SQLTools prepare auto completions for you.

PS: For a better experience, add this line to your sublime settings file

1. `CTRL+SHIFT+p`, select \"*Preferences: Settings - User*\"
2. add this option: 


```json
{
  \"auto_complete_triggers\": [
    {\"selector\": \"text.html\", \"characters\": \"<\" },
    {\"selector\": \"source.sql\", \"characters\": \".\"}
  ]
}
```
