# -*- coding: utf-8 -*-

# Copyright (c) 2017–2020 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Pytest fixtures for mocking Ansible modules."""

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from io import BytesIO
import json
import sys

import pytest

import ansible.module_utils.basic
from ansible.module_utils.common._collections_compat import MutableMapping
from ansible.module_utils.six import PY3, string_types
from ansible.module_utils._text import to_bytes


@pytest.fixture
def patch_ansible_module(monkeypatch, request):
    """Monkey-patch given Ansible module."""
    inp_args = request.param

    module_args_defaults = {
        '_ansible_keep_remote_files': False,
        '_ansible_remote_tmp': '/tmp',
    }

    if isinstance(inp_args, string_types):
        args = inp_args
    elif isinstance(inp_args, MutableMapping):
        mod_args = inp_args.get('ANSIBLE_MODULE_ARGS', inp_args)
        mod_args = dict(module_args_defaults, **mod_args)
        args = json.dumps({'ANSIBLE_MODULE_ARGS': mod_args})
    else:
        raise Exception(
            'Malformed data to the `patch_ansible_module` '
            'pytest fixture',
        )

    args = to_bytes(args)

    monkeypatch.setattr(ansible.module_utils.basic, '_ANSIBLE_ARGS', args)


@pytest.fixture
def stdin(mocker, monkeypatch, request):
    """Patch and return stdin buffer with module args."""
    monkeypatch.setattr(ansible.module_utils.basic, '_ANSIBLE_ARGS', None)
    monkeypatch.setattr(sys, 'argv', ['ansible_unittest'])

    if isinstance(request.param, string_types):
        args = request.param
    elif isinstance(request.param, MutableMapping):
        if 'ANSIBLE_MODULE_ARGS' not in request.param:
            request.param = {'ANSIBLE_MODULE_ARGS': request.param}
        if '_ansible_remote_tmp' not in request.param['ANSIBLE_MODULE_ARGS']:
            request.param['ANSIBLE_MODULE_ARGS']['_ansible_remote_tmp'] = '/tmp'
        if '_ansible_keep_remote_files' not in request.param['ANSIBLE_MODULE_ARGS']:
            request.param['ANSIBLE_MODULE_ARGS']['_ansible_keep_remote_files'] = False
        args = json.dumps(request.param)
    else:
        raise Exception('Malformed data to the stdin pytest fixture')

    fake_stdin_buffer = BytesIO(to_bytes(args, errors='surrogate_or_strict'))

    fake_stdin = mocker.MagicMock() if PY3 else fake_stdin_buffer
    if PY3:
        fake_stdin.buffer = fake_stdin_buffer

    monkeypatch.setattr(ansible.module_utils.basic.sys, 'stdin', fake_stdin)

    return fake_stdin_buffer


# pylint: disable=invalid-name,redefined-outer-name,unused-argument
@pytest.fixture
def am(stdin, request):
    """Return a patched Ansible module instance."""
    argspec = {}
    if isinstance(getattr(request, 'param', None), dict):
        argspec = request.param

    ans_mod = ansible.module_utils.basic.AnsibleModule(
        argument_spec=argspec,
    )
    ans_mod._name = 'ansible_unittest'  # pylint: disable=protected-access

    return ans_mod
