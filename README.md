pyj-tools - Python Jira Tools
=============================

This project contains a python library to use with Jira using the REST interface and several command line tools to 
perform several actions to the configured Jira repository.

# Configuration

## Command line
Using the pyjira.py library makes it possible to use standard configuration options, as there are:
- *-a* or *--address*: Base address of Jira instance
- *-u* or *--username*: User name for Jira
- *-p* or *--password*: Password for Jira
- *-d* or *--debug*: Use debug mode for logging

## Configuration file
If you do not want to always specify credentials on every call, you can use a configuration file *~/.jiracli*.
Put the file .jiracli into your home directory. It may contain the following values:
```
[server]
address=<address of jira installation>
username=<username>
password=<password>

[misc]
debug=<true|false>
```

A sample file would be:
```
[server]
address=https://jira.mycompany.net
username=marcschumacher
password=marcPassword

[misc]
debug=true
``` 