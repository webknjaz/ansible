# -*- coding: utf-8 -*-
#
# Copyright (c) 2017 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import json

import pytest


@pytest.mark.parametrize('ansible_module_args', [{}], indirect=['ansible_module_args'])
def test_warn(ansible_module, capfd):

    ansible_module.warn('warning1')

    with pytest.raises(SystemExit):
        ansible_module.exit_json(warnings=['warning2'])
    out, err = capfd.readouterr()
    assert json.loads(out)['warnings'] == ['warning1', 'warning2']


@pytest.mark.parametrize('ansible_module_args', [{}], indirect=['ansible_module_args'])
def test_deprecate(ansible_module, capfd):
    ansible_module.deprecate('deprecation1')
    ansible_module.deprecate('deprecation2', '2.3')

    with pytest.raises(SystemExit):
        ansible_module.exit_json(deprecations=['deprecation3', ('deprecation4', '2.4')])

    out, err = capfd.readouterr()
    output = json.loads(out)
    assert ('warnings' not in output or output['warnings'] == [])
    assert output['deprecations'] == [
        {u'msg': u'deprecation1', u'version': None},
        {u'msg': u'deprecation2', u'version': '2.3'},
        {u'msg': u'deprecation3', u'version': None},
        {u'msg': u'deprecation4', u'version': '2.4'},
    ]


@pytest.mark.parametrize('ansible_module_args', [{}], indirect=['ansible_module_args'])
def test_deprecate_without_list(ansible_module, capfd):
    with pytest.raises(SystemExit):
        ansible_module.exit_json(deprecations='Simple deprecation warning')

    out, err = capfd.readouterr()
    output = json.loads(out)
    assert ('warnings' not in output or output['warnings'] == [])
    assert output['deprecations'] == [
        {u'msg': u'Simple deprecation warning', u'version': None},
    ]
