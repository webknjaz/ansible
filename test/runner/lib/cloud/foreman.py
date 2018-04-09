#!/usr/bin/env python
"""Foreman plugin for integration tests."""

from __future__ import absolute_import, print_function

import os

from . import (
    CloudProvider,
    CloudEnvironment,
)

from ..util import (
    find_executable,
    display,
)

from ..docker_util import (
    docker_run,
    docker_rm,
    docker_inspect,
    docker_pull,
    get_docker_container_id,
)


class ForemanProvider(CloudProvider):
    """Foreman plugin.

    Sets up Foreman stub server for tests.
    """

    DOCKER_SIMULATOR_NAME = 'foreman-stub'
    DOCKER_SIMULATOR_IMAGE_NAME = 'ansible/foreman-test-container'
    DOCKER_SIMULATOR_IMAGE_TAG = '1.0.0'

    DOCKER_IMAGES = {
        'hub': {
            'registry_url': 'registry.hub.docker.com',
            'img_name': DOCKER_SIMULATOR_IMAGE_NAME,
            'img_tag': DOCKER_SIMULATOR_IMAGE_TAG,
        },
        'quay': {
            'registry_url': 'quay.io',
            'img_name': DOCKER_SIMULATOR_IMAGE_NAME,
            'img_tag': DOCKER_SIMULATOR_IMAGE_TAG,
        },
    }
    """Image registry to pull Foreman stub from.

    It's source source itself resides at:
    https://github.com/ansible/foreman-test-container
    """

    DOCKER_REGISTRY = 'quay'

    def __init__(self, args):
        """Set up container references for provider.

        :type args: TestConfig
        """
        super(ForemanProvider, self).__init__(
            args,
            config_extension='.foreman.yaml',
        )

        self.__container_from_env = os.getenv('ANSIBLE_FRMNSIM_CONTAINER')
        """Overrides target container, might be used for development.

        Use ANSIBLE_FRMNSIM_CONTAINER={hub|quay|whatever_you_want} if you want
        to be explicit. Omit/empty otherwise.
        """

        image_src = self.DOCKER_IMAGES.get(self.__container_from_env, {})
        if not image_src and self.__container_from_env:
            self.image = self.__container_from_env
        else:
            self.image = (
                # The simulator must be pinned to a specific version
                # to guarantee CI passes with the version used:
                '{registry_url}/{img_name}:{img_tag}'
            ).format(
                **(image_src or self.DOCKER_IMAGES[self.DOCKER_REGISTRY])
            )
        self.container_name = ''

    def filter(self, targets, exclude):
        """Filter out the tests with the necessary config and res unavailable.

        :type targets: tuple[TestTarget]
        :type exclude: list[str]
        """
        docker_cmd = 'docker'
        docker = find_executable(docker_cmd, required=False)

        if docker:
            return

        skip = 'cloud/%s/' % self.platform
        skipped = [target.name for target in targets if skip in target.aliases]

        if skipped:
            exclude.append(skip)
            display.warning(
                'Excluding tests marked "%s" '
                'which require the "%s" command: %s'
                % (skip.rstrip('/'), docker_cmd, ', '.join(skipped))
            )

    def setup(self):
        """Setup cloud resource before delegation and reg cleanup callback."""
        super(ForemanProvider, self).setup()

        if self._use_static_config():
            self._setup_static()
        else:
            self._setup_dynamic()

    def get_docker_run_options(self):
        """Get additional options needed when delegating tests to a container.

        :rtype: list[str]
        """
        return ['--link', self.DOCKER_SIMULATOR_NAME] if self.managed else []

    def cleanup(self):
        """Clean up the resource and temporary configs files after tests."""
        if self.container_name:
            docker_rm(self.args, self.container_name)

        super(ForemanProvider, self).cleanup()

    def _setup_dynamic(self):
        """Create a vcenter simulator using docker."""
        foreman_port = 8080
        container_id = get_docker_container_id()

        if container_id:
            display.info(
                'Running in docker container: %s' % container_id,
                verbosity=1,
            )

        self.container_name = self.DOCKER_SIMULATOR_NAME

        results = docker_inspect(self.args, self.container_name)

        if results and not results[0].get('State', {}).get('Running'):
            docker_rm(self.args, self.container_name)
            results = []

        display.info(
            '%s Foreman simulator docker container.'
            % ('Using the existing' if results else 'Starting a new'),
            verbosity=1,
        )

        if not results:
            if self.args.docker or container_id:
                publish_ports = []
            else:
                # publish the simulator ports when not running inside docker
                publish_ports = [
                    '-p', ':'.join((str(foreman_port), ) * 2),
                ]

            if not self.__container_from_env:
                docker_pull(self.args, self.image)

            docker_run(
                self.args,
                self.image,
                ['-d', '--name', self.container_name] + publish_ports,
            )

        if self.args.docker:
            foreman_host = self.DOCKER_SIMULATOR_NAME
        elif container_id:
            foreman_host = self._get_simulator_address()
            display.info(
                'Found Foreman simulator container address: %s'
                % foreman_host, verbosity=1
        )
        else:
            foreman_host = 'localhost'

        self._set_cloud_config('FOREMAN_HOST', foreman_host)
        self._set_cloud_config('FOREMAN_PORT', str(foreman_port))

    def _get_simulator_address(self):
        results = docker_inspect(self.args, self.container_name)
        ip_address = results[0]['NetworkSettings']['IPAddress']
        return ip_address

    def _setup_static(self):
        raise NotImplementedError


class ForemanEnvironment(CloudEnvironment):
    """Foreman environment plugin.

    Updates integration test environment after delegation.
    """

    def configure_environment(self, env, cmd):
        """
        :type env: dict[str, str]
        :type cmd: list[str]
        """

        # Send the container IP down to the integration test(s)
        env['FOREMAN_HOST'] = self._get_cloud_config('FOREMAN_HOST')
        env['FOREMAN_PORT'] = self._get_cloud_config('FOREMAN_PORT')
