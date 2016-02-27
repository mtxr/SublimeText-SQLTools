![SQLTools](/icon.png?raw=true) SQLTools
===============

A swiss knife for SQL in Sublime Text.

Project website: [http://mtxr.github.io/SQLTools/](http://mtxr.github.io/SQLTools/)

## Features
* View table schemas
* View Queries history
* Show table records
* Auto complete (PostgreSQL & MySQL)
* Run SQL Queries
* Threading Support (prevent ST lockups)
* Query timeout (Kill thread if query takes too long)
* Unescape chars for languages (PHP \" is replace by ")

## Todo

Up coming features:

- [ ] Save queries
- [ ] Get saved queries
- [ ] Run saved queries
- [ ] Auto complete for Oracle and Vertica

## Settings

| Option | Description | Type | Default value |
| --- | :--- | --- | --- |
| `unescape_quotes`| Escape chars like \" and \' for extension in array | `array` |`[ "php" ]` |
| `cli` | Path to desired command. You can check more on [Path to Cli](#path-to-commands) | `object` |  |
| `thread_timeout` | Query execution time in miliseconds before kill. Prevents Sublime Text from lockup while running complex queries | `int` | 5000 |
| `show_result_on_window` | Show query result using a window (true) or a panel (false) | `boolean` | `false` |
| `show_records` | Resultset settings. You can check more on [Show records options](#show-records-options) | `object` | `{"limit": 50}` |
| `format` | SQL formatting settings. You can check more on [SQL Formatting](#sql-formatting) | `object` | `{"limit": 50}` |

### <a id="show-records-options"></a>Show records options

| Option | Description | Type | Default value |
| --- | :--- | --- | --- |
| `limit`| number of rows to show whe using Show Table Records command | `int` | 50 |


### <a id="sql-formatting"></a>SQL Formatting

| Option | Description | Type | Default value |
| --- | :--- | --- | --- |
| `keyword_case` | Changes how keywords are formatted. Allowed values are `"upper"`, `"lower"` and `"capitalize"` and `null` (leaves case intact) | `string` | `"upper"` |
| `identifier_case` | Changes how identifiers are formatted. Allowed values are `"upper"` `"lower"` and `"capitalize"`and `null` (leaves case intact) | `string` | `null` |
| `strip_comments` | Remove comments from file/selection | `boolean` | `false` |
| `indent_tabs` | Use tabs instead of spaces | `boolean` | `false` |
| `indent_width` | Indentation width | `int` | 4 |
| `reindent` | Reindent code if `true` | `boolean` | `true` |

### <a id="path-to-commands"></a>Path to Cli

In case your database command is not in your `PATH` enviroment var, you can set the path here.

| Option | Default value |
| --- | --- |
| `mysql`|  `"mysql"` |
| `pgsql` | `"psql"` |
| `oracle` | `"sqlplus"` |
| `vertica` | `"vsql"` |

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
            "database": "dbname"
        },
        "Connection 2": {
            "type"    : "pgsql",
            "host"    : "127.0.0.1",
            "port"    :  5432,
            "username": "anotheruser",
            "database": "dbname"
        },
        "Connection 3": {
            "type"    : "oracle",
            "host"    : "127.0.0.1",
            "port"    :  1522,
            "username": "anotheruser",
            "password": "password",
            "database": "dbname",
            "service" : "servicename"
        }
    },
    "default": "Connection 1"
}
```


## Auto Complete

After you select one connection, SQLTools prepare auto completions for you.

PS: For a better experience, add this line to your sublime settings file

1. `CTRL+SHIFT+P`, select "*Preferences: Settings - User*"
2. add this option: 


```
"auto_complete_triggers": [ {"selector": "text.html", "characters": "<"}, {"selector": "source.sql", "characters": "."} ]
```
