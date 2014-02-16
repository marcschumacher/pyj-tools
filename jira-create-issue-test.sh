#!/bin/bash
./jira-create-issue.py --debug \
--project PPD \
--summary "Sample title" \
--type Improvement \
--assignee mschumacher \
--reporter mschumacher \
--labels ongoing,testlabel \
--environment "testenvironment" \
--fix-versions R13_00_50,R14_00_02 \
--priority Major \
--due-date 2013-12-30 \
--description "My little description" \
--components "Engine,CDA" \
--original-estimate "12h" \
--transition-to "Ready 4 Dev" \
developer=mschumacher reviewer=mschumacher security-risk=Unchecked