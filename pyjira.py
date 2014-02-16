#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import logging
import ConfigParser
import sys
import os

import requests


class JiraResult:
	def __init__(self, log, status_code, json):
		self.log = log
		self.status_code = status_code
		self.json = json
		self.log.debug('JSON result: %s' % self.json)
		self.log.debug('Status code: %s' % self.status_code)

	def is_error(self):
		return self.status_code >= 300

	def is_success(self):
		return not self.is_error()

	def __str__(self):
		return "<%s> <%s>" % (self.status_code, self.json)

	def log_error(self, msg=None):
		if msg:
			self.log.error(msg)
		for error_message in self.json['errorMessages']:
			self.log.error(error_message)
		if 'errors' in self.json:
			for key in self.json['errors'].keys():
				self.log.error('%s: %s' % (key, self.json['errors'][key]))


class JiraServerConfiguration:
	def __init__(self):
		self.address = None
		self.username = None
		self.password = None
		self.custom_field_configuration = None
		self.debug = False
		self.jira_version = '5'

	def enrich_options(self, parser):
		parser.add_option('-a', '--address', help='Base address of Jira instance')
		parser.add_option('-u', '--username', help='User name for Jira')
		parser.add_option('-p', '--password', help='Password for Jira')
		parser.add_option('-d', '--debug', help='Use debug mode for logging', action='store_true', default=False)

	def parse_configuration_file(self):
		config = ConfigParser.RawConfigParser()
		# Is the configuration file existant?
		if len(config.read('%s/.jiracli' % os.getenv('HOME'))) > 0:
			self.address = config.get('server', 'address')
			self.username = config.get('server', 'username')
			self.password = config.get('server', 'password')
			try:
				self.debug = config.getboolean('misc', 'debug')
			except:
				pass
		self.log = self.init_logging(self.debug)
		self.parse_custom_fields(config)

	def parse_custom_fields(self, config):
		self.custom_field_configuration = {}
		for item in config.items('customField'):
			section_key = item[0]
			value = item[1]
			split_section_key = section_key.split('.')
			section = split_section_key[0]
			key = split_section_key[1]

			if (not self.custom_field_configuration.has_key(section)):
				self.custom_field_configuration[section] = {}
			self.custom_field_configuration[section][key] = value

	# If no parser is specified, only the configuration file is used for authentification
	def parse_configuration(self, parser=None):
		options = {}
		args = []

		self.parse_configuration_file()

		if parser:
			options, args = parser.parse_args()
			if options.address:
				self.address = options.address
			if options.username:
				self.username = options.username
			if options.password:
				self.password = options.password
			if options.debug:
				self.debug = options.debug

		if not self.address:
			parser.error('Please specify a server address either as parameter (-a) or in config file (~/.jiracli)!')

		if not self.username:
			parser.error('Please specify a user name either as parameter (-a) or in config file (~/.jiracli)!')

		if not self.password:
			parser.error('Please specify a password either as parameter (-a) or in config file (~/.jiracli)!')

		self.log = self.init_logging(self.debug)

		return options, args, self.log

	def init_logging(self, debug_mode):
		logger = logging.getLogger(__name__)
		logging.basicConfig(level=logging.WARN, format='%(levelname)s -- %(message)s')
		if debug_mode:
			logging.getLogger(__name__).setLevel(logging.DEBUG)
		else:
			logging.getLogger(__name__).setLevel(logging.INFO)
		return logger

	def connect(self):
		self.jc = JiraConnection(self.address, self.log, self.jira_version)
		login_result = self.jc.login(self.username, self.password)

		if login_result.is_error():
			login_result.log_error("Error during login!")
			sys.exit(1)
		self.log.debug('Login successful')
		return self.jc

	def disconnect(self):
		status = self.jc.logout()
		if status == 204:
			self.log.debug('Logout successful!')
		else:
			self.log.warning('Error during logging out (status %s)!' % status)

	def get_issue_url(self, issue_key):
		return "%s/browse/%s" % (self.address, issue_key)

	def add_configured_custom_value(self, valueHash, key, value):
		if self.custom_field_configuration.has_key(key):
			config = self.custom_field_configuration[key]
			type = config['type']
			if type == 'additionalHash':
				fieldname = config['fieldname']
				fieldsubname = config['fieldsubname']
				self.add_hash_value(fieldname, fieldsubname, valueHash, value)
			else:
				self.log.error('Unknown type %s!' % type)
		else:
			self.log.error('Unable to find custom field definition for %s!' % key)

	def add_hash_value(self, valueName, name, valueHash, value):
		if value:
			valueHash[valueName] = {}
			valueHash[valueName][name] = value


class JiraConnection:
	def __init__(self, base_url, log, jira_version):
		self.static_rest_configuration = {
		'4.4': {
		'api_name_api': '/rest/api/2.0.alpha1',
		'api_name_auth': '/rest/auth/1',
		},
		'5': {
		'api_name_api': '/rest/api/2',
		'api_name_auth': '/rest/auth/1',
		}
		}
		self.rest_configuration = self.static_rest_configuration[jira_version]
		self.base_url = base_url
		if log:
			self.log = log
		else:
			self.log = logging.getLogger(__name__)
			logging.getLogger(__name__).setLevel(logging.DEBUG)
		self.cookies = None
		self.api_name_api = self.rest_configuration['api_name_api']
		self.api_name_auth = self.rest_configuration['api_name_auth']

	def perform_request(self, method, prefix_path, path, json_data=None):
		if not json_data:
			json_data = {}
		url = self.base_url + prefix_path + path
		self.log.debug('Request: (%s) %s' % (method, url))
		self.log.debug('JSON parameter: %s' % json.dumps(json_data))
		result = requests.request(method, url, cookies=self.cookies, data=json.dumps(json_data),
								  headers={'Content-Type': 'application/json'})
		self.log.debug(result.text)
		json_result = None
		if result.text:
			json_result = result.json()
		return JiraResult(self.log, result.status_code, json_result)

	def perform_api_request(self, method, path, json_data=None):
		return self.perform_request(method, self.api_name_api, path, json_data)

	def perform_auth_request(self, method, path, json_data=None):
		return self.perform_request(method, self.api_name_auth, path, json_data)

	def perform_api_get_request(self, path, json_data=None):
		return self.perform_api_request('get', path, json_data)

	def perform_api_post_request(self, path, json_data=None):
		return self.perform_api_request('post', path, json_data)

	def perform_api_delete_request(self, path, json_data=None):
		return self.perform_api_request('delete', path, json_data)

	def perform_api_put_request(self, path, json_data=None):
		return self.perform_api_request('put', path, json_data)

	def login(self, username, password):
		self.log.debug('LOGIN')
		url = self.base_url + self.api_name_auth + '/session'
		json_data = {'username': username, 'password': password}
		self.log.debug('Request: (%s) %s' % ('post', url))
		self.log.debug('JSON parameter: %s' % json.dumps(json_data))
		result = requests.post(url, cookies=self.cookies, data=json.dumps(json_data),
							   headers={'content-type': 'application/json'})
		self.cookies = result.cookies
		self.log.debug(result.text)
		return JiraResult(self.log, result.status_code, result.json())

	def logout(self):
		self.log.debug('LOGOUT')
		path = self.base_url + self.api_name_auth + '/session'
		return requests.delete(path, cookies=self.cookies).status_code

	def create_issue(self, project, summary, issuetype, additional_fields=None):
		self.log.debug('CREATE_ISSUE')
		path = '/issue/'
		fields = {'project': {'key': project}, 'summary': summary, 'issuetype': {'name': issuetype}}
		if additional_fields:
			fields.update(additional_fields)
		json_data = {'fields': fields}
		return self.perform_api_post_request(path, json_data)

	def create_issue_link(self, link_type, from_issue_key, to_issue_key):
		path = '/issueLink'
		json_data = {'type': {'name': link_type}, 'inwardIssue': {'key': from_issue_key},
					 'outwardIssue': {'key': to_issue_key}}
		return self.perform_api_post_request(path, json_data)

	def get_issue_info(self, issue_key):
		return self.perform_api_get_request('/issue/' + issue_key)

	def get_issue_transitions(self, issue_key):
		return self.perform_api_get_request('/issue/%s/transitions' % issue_key)

	def perform_issue_transitions_by_name(self, issue_key, transition_name):
		transition_id = -1
		result = self.get_issue_transitions(issue_key)
		self.log.debug("Trying to find possible transition to %s..." % transition_name)
		if result.is_success():
			transitions = result.json['transitions']
			for transition in transitions:
				name = transition['to']['name']
				id = transition['id']
				if transition_name == name:
					transition_id = id
					self.log.info("Found transaction %s." % transition_id)
					break
		return self.perform_issue_transition_by_id(issue_key, transition_id)

	def perform_issue_transition_by_id(self, issue_key, transition_id):
		self.log.debug("Trying to transition to %s..." % transition_id)
		path = '/issue/%s/transitions?%s' % (issue_key, transition_id)
		json_data = {'transition': {'id': transition_id}}
		return self.perform_api_post_request(path, json_data)

	def remove_issue_vote(self, issue_key):
		path = '/issue/%s/votes' % issue_key
		return self.perform_api_delete_request(path)

	def cast_issue_vote(self, issue_key):
		path = '/issue/%s/votes' % issue_key
		return self.perform_api_post_request(path)

	def get_issue_votes(self, issue_key):
		return self.perform_api_get_request('/issue/%s/votes' % issue_key)

	def get_issue_watchers(self, issue_key):
		return self.perform_api_get_request('/issue/%s/watchers' % issue_key)

	def add_issue_watcher(self, issue_key):
		# TODO TEST!
		# Check!
		path = '/issue/%s/watchers' % issue_key
		return self.perform_api_post_request(path)

	def remove_issue_watcher(self, issue_key, username):
		# TODO TEST!
		path = '/issue/%s/watchers?username=%s' % (issue_key, username)
		return self.perform_api_delete_request(path)

	def get_current_user_information(self):
		return self.perform_auth_request('get', '/session')

	def create_project_version(self, name, project, release_date=None, description=None, user_release_date=None,
							   released=False, archived=False):
		path = '/version'
		json_data = {'name': name, 'project': project}

		if description:
			json_data['description'] = description

		if user_release_date:
			json_data['userReleaseDate'] = user_release_date

		if release_date:
			json_data['releaseDate'] = release_date

		if released:
			json_data['released'] = 'true'
		else:
			json_data['released'] = 'false'

		if archived:
			json_data['archived'] = 'true'
		else:
			json_data['archived'] = 'false'

		return self.perform_api_post_request(path, json_data)

	def remove_project_version(self, id, move_fixed_dest='', move_affected_dest=''):
		# TODO TEST!
		path = '/version/%s?moveFixIssuesTo=%s&moveAffectedIssuesTo=%s' % (id, move_fixed_dest, move_affected_dest)
		return self.perform_api_delete_request(path)

	def get_project_version(self, id):
		# TODO TEST!
		return self.perform_api_get_request('/version/%s' % id)

	def modify_project_version(
			self,
			id,
			name,
			description,
			overdue,
			user_release_date,
			release_date,
			released,
			archived,
	):

		# TODO TEST!
		path = '/version/%s' % id
		json_data = {
		'description': description,
		'name': name,
		'overdue': overdue,
		'userReleaseDate': user_release_date,
		'releaseDate': release_date,
		'released': released,
		'archived': archived,
		}
		return self.perform_api_put_request(path, json_data)

	def get_project_version_related_issue_count(self, id):
		# TODO TEST!
		return self.perform_api_get_request('/version/%s/relatedIssueCounts' % id)

	def get_project_version_unresolved_issue_count(self, id):
		# TODO TEST!
		return self.perform_api_get_request('/version/%s/unresolvedIssueCount' % id)

	def move_project_version_position(self, id, position):
		# TODO TEST!
		path = '/version/%s/move' % id
		json_data = {'position': position}
		return self.perform_api_post_request(path, json_data)

	def get_issue_comment(self, id):
		# TODO TEST!
		return self.perform_api_get_request('/comment/%s' % id)

	def get_project_role(self, project_key, id):
		# TODO TEST!
		return self.perform_api_get_request('/project/%s/role/%s' % (project_key, id))

	def get_user(self, username):
		# TODO TEST!
		return self.perform_api_get_request('/user?%s' % username)

	def get_server_info(self):
		# TODO TEST!
		return self.perform_api_get_request('/serverInfo')

	def create_component(self, project, name, description):
		# TODO TEST!
		path = '/component'
		json_data = {'project': project, 'name': name, 'description': description}
		return self.perform_api_post_request(path, json_data)

	def delete_component(self, id, issue_dest):
		# TODO TEST!
		path = '/component/%s?moveIssuesTo=%s' % (id, issue_dest)
		return self.perform_api_delete_request(path)

	def get_component(self, id):
		# TODO TEST!
		return self.perform_api_get_request('/component/%s' % id)

	def modify_component(self, id, project, name, description):
		# TODO TEST!
		path = '/component/%s' % id
		json_data = {'project': project, 'name': name, 'description': description}
		return self.perform_api_put_request(path, json_data)

	def get_component_related_issue_count(self, id):
		# TODO TEST!
		return self.perform_api_get_request('/component/%s/relatedIssueCounts' % id)

	def search(self, jql, start_at, max_results, fields):
		# TODO TEST!
		request_path = '/search'
		json_data = {'jql': jql, 'startAt': start_at, 'maxResults': max_results, 'fields': fields}
		return self.perform_api_post_request(request_path, json_data)

	def get_projects(self):
		# TODO TEST!
		return self.perform_api_get_request('/project')

	def get_project(self, key):
		# TODO TEST!
		return self.perform_api_get_request('/project/%s' % key)

	def get_project_versions(self, key):
		# TODO TEST!
		return self.perform_api_get_request('/project/%s/versions' % key)

	def get_project_components(self, key):
		# TODO TEST!
		return self.perform_api_get_request('/project/%s/components' % key)

	def get_status(self, id):
		# TODO TEST!
		return self.perform_api_get_request('/status/%s' % id)

	def get_issue_link_types(self):
		# TODO TEST!
		return self.perform_api_get_request('/issueLinkType')

	def get_issue_link_type(self, issue_link_type_id):
		# TODO TEST!
		return self.perform_api_get_request('/issueLinkType/%s' % issue_link_type_id)

	def get_custom_field_option(self, id):
		# TODO TEST!
		return self.perform_api_get_request('/customFieldOption/%s' % id)

	def get_resolution(self, id):
		# TODO TEST!
		return self.perform_api_get_request('/resolution/%s' % id)

	def get_issue_type(self, id):
		# TODO TEST!
		return self.perform_api_get_request('/issueType/%s' % id)

	def get_attachment(self, id):
		# TODO TEST!
		return self.perform_api_get_request('/attachment/%s' % id)

	def get_issue_priority(self, id):
		# TODO TEST!
		return self.perform_api_get_request('/priority/%s' % id)

	def get_worklog(self, id):
		# TODO TEST!
		return self.perform_api_get_request('/worklog/%s' % id)

	def add_issue_attachment(self, issue_key, file):
		# TODO TEST!
		url = self.base_url + self.api_name_api + '/issue/%s/attachments' % issue_key
		file = {'file': open(file, 'rb')}
		result = requests.post(url, cookies=self.cookies, files=file)
		return JiraResult(self.log, result.status_code, result.json())

	def update_filter(self, id, jql):
		return self.perform_api_put_request('/filter/%s' % id, json_data={'jql': jql})

	def get_all_fields(self):
		return self.perform_api_get_request('/field')
