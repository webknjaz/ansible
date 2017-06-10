# -*- coding: utf-8 -*-
# Copyright (C) 2016 Guido Günther <agx@sigxcpu.org>, Daniel Lobato Garcia <dlobatog@redhat.com>
# Copyright (c) 2017 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = '''
    name: foreman
    plugin_type: inventory
    short_description: foreman inventory source
    description:
        - Get inventory hosts from the foreman service.
    options:
      url:
        description: url to foreman
        default: 'http://localhost:300'
      user:
        description: foreman authentication user
      password:
        description: forman authentication password
      validate_certs:
        description: verify SSL certificate if using https
        default: False
      group_prefix:
        description: prefix to apply to foreman groups
        default: foreman_
      want_facts:
        description: Toggle to retrieve host facts or not from the server
        type: boolean
'''

import re

from collections import MutableMapping
from distutils.version import LooseVersion

from ansible.errors import AnsibleError
from ansible.module_utils._text import to_bytes, to_native
from ansible.plugins.inventory import BaseInventoryPlugin

# 3rd party imports
try:
    import requests
    if LooseVersion(requests.__version__) < LooseVersion('1.1.0'):
        raise ImportError
except ImportError:
        raise AnsibleError('This script requires python-requests 1.1 as a minimum version')

from requests.auth import HTTPBasicAuth


class InventoryModule(BaseInventoryPlugin):
    ''' Host inventory parser for ansible using foreman as source. '''

    NAME = 'foreman'

    def __init__(self):

        super(InventoryModule, self).__init__()

        # from config
        self.foreman_url = None
        self.foreman_user = None
        self.foreman_pw = None
        self.foreman_ssl_verify = True

        self.group_prefix = 'foreman_'

        self.session = None
        self.cache = {}
        self.do_cache = True

    def verify_file(self, path):

        valid = False
        if super(InventoryModule, self).verify_file(path):
            if path.endswith('.foreman.yaml') or path.endswith('.foreman.yml'):
                valid = True
        return valid

    def _get_session(self):
        if not self.session:
            self.session = requests.session()
            self.session.auth = HTTPBasicAuth(self.foreman_user, self.foreman_pw)
            self.session.verify = self.foreman_ssl_verify
        return self.session

    def _get_json(self, url, ignore_errors=None):

        if not self.do_cache or url not in self.cache:

            page = 1
            results = []
            s = self._get_session()
            while True:
                ret = s.get(url, params={'page': page, 'per_page': 250})
                if ignore_errors and ret.status_code in ignore_errors:
                    break
                ret.raise_for_status()
                json = ret.json()
                # /hosts/:id has not results key
                if 'results' not in json:
                    return json
                # Facts are returned as dict in results not list
                if isinstance(json['results'], MutableMapping):
                    return json['results']
                # List of all hosts is returned paginaged
                results = results + json['results']
                if len(results) >= json['total']:
                    break
                page += 1
                if len(json['results']) == 0:
                    self.display.warning("Did not make any progress during loop. expected %d got %d" % (json['total'], len(results)))
                    break

            self.cache[url] = results

        return self.cache[url]

    def _get_hosts(self):
        return self._get_json("%s/api/v2/hosts" % self.foreman_url)

    def _get_all_params_by_id(self, hid):
        url = "%s/api/v2/hosts/%s" % (self.foreman_url, hid)
        ret = self._get_json(url, [404])
        if not ret or not isinstance(ret, MutableMapping) or not ret.get('all_parameters', False):
            ret = {'all_parameters': [{}]}
        return ret.get('all_parameters')[0]

    def _get_facts_by_id(self, hid):
        url = "%s/api/v2/hosts/%s/facts" % (self.foreman_url, hid)
        return self._get_json(url)

    def _get_facts(self, host):
        """Fetch all host facts of the host"""
        if not self.get_option('want_facts'):
            return {}

        ret = self._get_facts_by_id(host['id'])
        if len(ret.values()) == 0:
            facts = {}
        elif len(ret.values()) == 1:
            facts = list(ret.values())[0]
        else:
            raise ValueError("More than one set of facts returned for '%s'" % host)
        return facts

    def to_safe(self, word):
        '''Converts 'bad' characters in a string to underscores so they can be used as Ansible groups
        #> ForemanInventory.to_safe("foo-bar baz")
        'foo_barbaz'
        '''
        regex = "[^A-Za-z0-9\_]"
        return re.sub(regex, "_", word.replace(" ", ""))

    def _populate(self):

        for host in self._get_hosts():

            if host.get('name'):
                self.inventory.add_host(host['name'])

            # create directly mapped groups
            group_name = host.get('hostgroup_title', host.get('hostgroup_name'))
            if group_name:
                group_name = self.to_safe('%s%s' % (self.group_prefix, group_name.lower()))
                self.inventory.add_group(group_name)
                self.inventory.add_child(group_name, host['name'])

            # set host vars
            try:
                for k, v in self._get_all_params_by_id(host['id']):
                    self.inventory.set_variable(host['name'], k, v)
            except ValueError as e:
                self.display.warning("Could not unpack params for %s, skipping: %s" % (host, to_native(e)))

            # set facts
            self.inventory.set_variable(host['name'], 'ansible_facts', self._get_facts(host))

    def parse(self, inventory, loader, path, cache=True):

        super(InventoryModule, self).parse(inventory, loader, path)

        #TODO: enable caching
        #self.do_cache = cache
        #cache_key = self.get_cache_prefix(path)
        #if cache_key not in inventory.cache:
        #    inventory.cache[cache_key] = {}
        #self.cache = inventory.cache[cache_key]

        # read config from file, this sets 'options'
        self._read_config_data(path)

        # get connection settings
        self.foreman_url = self.get_option('url')
        self.foreman_pw = to_bytes(self.get_option('password'))
        self.foreman_user = self.get_option('user')
        self.foreman_ssl_verify = self.get_option('validate_certs')

        # other options
        self.group_prefix = self.get_option('group_prefix')

        # actually populate inventory
        self._populate()
