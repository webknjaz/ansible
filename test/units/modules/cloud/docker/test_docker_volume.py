# Copyright (c) 2018 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import json

import pytest

from ansible.modules.cloud.docker import docker_volume
from ansible.module_utils._json_streams_rfc7464 import read_json_documents
from ansible.module_utils._text import to_bytes
from ansible.module_utils.six import BytesIO
from ansible.module_utils.docker import common

pytestmark = pytest.mark.usefixtures('patch_ansible_module')

TESTCASE_DOCKER_VOLUME = [
    {
        'name': 'daemon_config',
        'state': 'present'
    }
]


@pytest.mark.parametrize('patch_ansible_module', TESTCASE_DOCKER_VOLUME, indirect=['patch_ansible_module'])
def test_create_volume_on_invalid_docker_version(mocker, capfd):
    mocker.patch.object(common, 'HAS_DOCKER_PY', True)
    mocker.patch.object(common, 'docker_version', '1.8.0')

    with pytest.raises(SystemExit):
        docker_volume.main()

    out, _err = capfd.readouterr()
    b_out = to_bytes(out)  # capfdbinary is unavailable under Python 2.6
    results = next(read_json_documents(BytesIO(b_out)))
    assert results['failed']
    assert 'Error: Docker SDK for Python version is 1.8.0 ' in results['msg']
    assert 'Minimum version required is 1.10.0.' in results['msg']
