#! /usr/bin/env bash

[[ -n "$DEBUG" ]] && set -x

set -euo pipefail

ansible-playbook test_foreman_inventory.yml -v "$@"
