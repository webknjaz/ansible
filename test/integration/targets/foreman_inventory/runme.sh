#!/usr/bin/env bash

[[ -n "$DEBUG" || -n "$ANSIBLE_DEBUG" ]] && set -x

set -euo pipefail

export ANSIBLE_CONFIG=ansible.cfg
FOREMAN_CONFIG=test-config.foreman.yaml

function _cleanup() {
    echo Cleanup: removing $FOREMAN_CONFIG...
    rm -vf "$FOREMAN_CONFIG"
    unset ANSIBLE_CONFIG
    unset FOREMAN_CONFIG
}
trap _cleanup INT TERM EXIT

cat > "$FOREMAN_CONFIG" <<FOREMAN_YAML
plugin: foreman
url: http://${FOREMAN_HOST}:${FOREMAN_PORT}
user: ansible-tester
password: secure
validate_certs: False
FOREMAN_YAML

ansible-playbook test_foreman_inventory.yml --connection=local -v "$@"
