# Copyright: (c) 2019, Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import pytest

from ansible.module_utils._json_streams_rfc7464 import read_json_documents
from ansible.module_utils._text import to_bytes
from ansible.module_utils.six import BytesIO
from ansible.modules.cloud.misc import terraform
from units.modules.utils import set_module_args


def test_terraform_without_argument(capfd):
    set_module_args({})
    with pytest.raises(SystemExit) as results:
        terraform.main()

    out, err = capfd.readouterr()
    b_out = to_bytes(out)  # capfdbinary is unavailable under Python 2.6
    results = next(read_json_documents(BytesIO(b_out)))
    assert not err
    assert results['failed']
    assert 'project_path' in results['msg']
