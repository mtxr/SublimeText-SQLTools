SQLTools
===============

A swiss knife for SQL in Sublime Text.

Inspired by [SQLExec Plugin](http://lubriciousdevelopers.github.io/projects/sublime-sql-exec/) and [SqlBeautifier](https://github.com/zsong/SqlBeautifier).

## Features
* View table schemas
* Show table records
* Run SQL Queries
* Threading Support (prevent ST lockups)
* Query timeout (Kill thread if query takes too long)
* Unescape chars for languages (PHP \" is replace by ")

## Settings

| Option | Description | Default value |
| --- | :--- | --- |
| `unescape_quotes`| Escape chars like \" and \' for extension in array | `[ "php" ]` |
| `commands` | Path to desired command | `{ "mysql"  : "mysql", "pgsql"  : "psql", "oracle" : "sqlplus", "vertica": "vsql" }` |
| `debug` | Activate debug mode. This will print SQL queries and messages using Sublime Text console | `false` |
| `thread_timeout` | Query execution time in miliseconds before kill. Prevents Sublime Text from lockup while running complex queries | 5000 |
| `show_result_on_window` | Show query result using a window (true) or a panel (false) | `false` |
| `show_records` | Resultset settings. you can check more on [Show records options](#show-records-options). | `{"limit": 50}` |

### <a id="show-records-options"></a>Show records options

| Option | Description | Default value |
| --- | :--- | --- |
| `limit`| number of rows to show whe using Show Table Records command | `50` |
