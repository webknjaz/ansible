#! /usr/bin/env bash

set -euo pipefail

[[ -n "$DEBUG" ]] && set -x

ansible-playbook test_foreman_inventory -v "$@"
