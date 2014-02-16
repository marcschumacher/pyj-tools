#!/usr/bin/python
# -*- coding: utf-8 -*-

from optparse import OptionParser

from pyjira import JiraServerConfiguration


def main():
	jsc = JiraServerConfiguration()

	parser = OptionParser('%prog [options] <project> <version-name>')
	parser.add_option('-e', '--description', help='Description for this version')
	parser.add_option('-r', '--release-date', help='Planned release date for this version')

	jsc.enrich_options(parser)
	options, args, log = jsc.parse_configuration(parser)

	if len(args) != 2:
		parser.error('Please specify both project and version name!')

	project = args[0]
	version_name = args[1]

	if not project:
		parser.error('Please specify a project to use!')

	if not version_name:
		parser.error('Please specify a version name to use!')

	description = options.description
	release_date = options.release_date

	jc = jsc.connect()

	log.debug('Trying to create version %s for project %s with release date %s and description: %s' % (
	version_name, project, release_date, description))
	result = jc.create_project_version(version_name, project, release_date, description)

	log.debug('JSON result: %s' % result.json)
	log.debug('Status code: %s' % result.status_code)
	if result.is_success():
		log.info('Creation of version %s for %s was successful!' % (version_name, project))
	else:
		log.error('Error while trying to create version!')
		for error_message in result.json['errorMessages']:
			log.error(error_message)
		for key in result.json['errors'].keys():
			log.error('%s: %s' % (key, result.json['errors'][key]))

	jsc.disconnect()


if __name__ == '__main__':
	main()
