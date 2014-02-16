#!/usr/bin/python
# -*- coding: utf-8 -*-

from optparse import OptionParser

from pyjira import JiraServerConfiguration


def add_simple_value(valueName, valueHash, value):
	if value:
		valueHash[valueName] = value


def parse_custom_fields(jsc, field_definitions, valueHash):
	for field_def in field_definitions:
		split_option = field_def.split('=')
		if len(split_option) != 2:
			jsc.log.error("ERROR parsing custom field: %s! Syntax: 'key=value'" % field_def)
		else:
			key = split_option[0]
			value = split_option[1]
			jsc.add_configured_custom_value(valueHash, key, value)


def main():
	jsc = JiraServerConfiguration()

	parser = OptionParser('%prog [options] [custom-fields]')
	jsc.enrich_options(parser)

	parser.add_option('-j', '--project', help='Project to use')
	parser.add_option('-s', '--summary', help='Title to use')
	parser.add_option('-t', '--type', help='Type of issue to use (e.g. "Bug", "Improvement")', default='Bug')

	parser.add_option('-n', '--assignee', help='Assignee to set the issue to')
	parser.add_option('-r', '--reporter', help='Reporter to set the issue to')

	parser.add_option('-l', '--labels', help='Label to add to issue (comma separated)')
	parser.add_option('-e', '--environment', help='Environment to set the issue to')
	parser.add_option('-f', '--fix-versions', help='Fix versions to set the issue to (comma separated)')
	parser.add_option('-o', '--priority', help='Priority to set the issue to')
	parser.add_option('', '--due-date', help='Due date to set the issue to')
	parser.add_option('', '--description', help='Description to set the issue to')
	parser.add_option('-c', '--components', help='Components to set the issue to (comma separated)')
	parser.add_option('', '--original-estimate', help='Original estimate to set the issue to')

	parser.add_option('', '--developer', help='Developer to set the issue to')
	parser.add_option('', '--reviewer', help='Reviewer to set the issue to')
	parser.add_option('', '--security-risk', help='Security risk to set the issue to')
	parser.add_option('', '--cost-attribution', help='Cost attribution to set the issue to')
	parser.add_option('', '--transition-to', help='Move issue to specified status')

	options, args, log = jsc.parse_configuration(parser)

	if not options.project:
		parser.error('Project (-j) is required!')

	if not options.summary:
		parser.error('Summary (-s) is required!')

	additional_options = {}

	if len(args) > 0:
		parse_custom_fields(jsc, args, additional_options)

	jsc.add_hash_value('assignee', 'name', additional_options, options.assignee)
	jsc.add_hash_value('reporter', 'name', additional_options, options.reporter)
	jsc.add_hash_value('priority', 'name', additional_options, options.priority)
	jsc.add_hash_value('timetracking', 'originalEstimate', additional_options, options.original_estimate)

	add_simple_value('duedate', additional_options, options.due_date)
	add_simple_value('description', additional_options, options.description)
	add_simple_value('environment', additional_options, options.environment)

	if options.labels:
		additional_options['labels'] = options.labels.split(',')

	if options.fix_versions:
		fix_version_list = []
		for fix_version in options.fix_versions.split(','):
			fix_version_list.append({'name': fix_version})
		additional_options['fixVersions'] = fix_version_list

	if options.components:
		component_list = []
		for component in options.components.split(','):
			component_list.append({'name': component})
		additional_options['components'] = component_list

	#jsc.add_hash_value('customfield_10344', 'name', additional_options, options.developer)
	#jsc.add_hash_value('customfield_12089', 'name', additional_options, options.reviewer)
	#jsc.add_hash_value('customfield_15362', 'value', additional_options, options.security_risk)
	#jsc.add_hash_value('customfield_15369', 'value', additional_options, options.cost_attribution)

	log.debug('Additional options: %s' % additional_options)

	jc = jsc.connect()

	log.debug('Creating issue of type "%s" for project "%s" with summary "%s"...' % (options.type, options.project,
																					 options.summary))
	result = jc.create_issue(options.project, options.summary, options.type, additional_options)
	status_code = result.status_code
	json_result = result.json
	log.debug('JSON result: %s' % json_result)
	log.debug('Status code: %s' % status_code)
	if result.is_success():
		key = json_result['key']
		log.info('Issue created: %s.' % key)
		if options.transition_to:
			transitionTo = options.transition_to
			log.info("Trying to move ticket to %s..." % transitionTo)
			transitionResult = jc.perform_issue_transitions_by_name(key, transitionTo)
			if transitionResult.is_success():
				log.info("Transition of %s to %s successful." % (key, transitionTo))
			else:
				log.error("Transition of issue %s to %s failed!" % (key, transitionTo))
	else:
		result.log_error('Unable to create issue!')

	jsc.disconnect()


if __name__ == '__main__':
	main()
