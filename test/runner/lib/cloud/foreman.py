#! /usr/bin/env python
"""Foreman plugin for integration tests."""

from __future__ import absolute_import, print_function

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

    DOCKER_SIMULATOR_NAME = 'foreman-simulator'

    def __init__(self, args):
        """Set up container references for provider.

        :type args: TestConfig
        """
        super(ForemanProvider, self).__init__(
            args,
            config_extension='.foreman.yaml',
        )

        self.__container_from_env = os.getenv('ANSIBLE_FRMNSIM_CONTAINER')
        self.image = self.__container_from_env or (
            'ansible/ansible:%s'
            # The simulator must be pinned to a specific version
            # to guarantee CI passes with the version used:
            '@sha256:soooomeinvaaalidddshaaa'
        ) % self.DOCKER_SIMULATOR_NAME
        self.container_name = ''

    def filter(self, targets, exclude):
        """Filter out the cloud tests when the necessary config and resources are not available.

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
                'Excluding tests marked "%s" which require the "%s" command: %s'
                % (skip.rstrip('/'), docker_cmd, ', '.join(skipped))
            )

    def setup(self):
        """Setup the cloud resource before delegation and register a cleanup callback."""
        super(ForemanProvider, self).setup()

        if self._use_static_config():
            self._setup_static()
        else:
            self._setup_dynamic()

    def get_docker_run_options(self):
        """Get any additional options needed when delegating tests to a docker container.

        :rtype: list[str]
        """
        return ['--link', self.DOCKER_SIMULATOR_NAME] if self.managed else []

    def cleanup(self):
        """Clean up the cloud resource and any temporary configuration files after tests complete."""
        if self.container_name:
            docker_rm(self.args, self.container_name)

        super(ForemanProvider, self).cleanup()

    def _setup_dynamic(self):
        """Create a vcenter simulator using docker."""
	foreman_port = 8080
        container_id = get_docker_container_id()

        if container_id:
            display.info('Running in docker container: %s' % container_id, verbosity=1)

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
            display.info('Found Foreman simulator container address: %s' % foreman_host, verbosity=1)
        else:
            foreman_host = 'localhost'

        self._set_cloud_config('foreman_host', foreman_host)
        self._set_cloud_config('foreman_port', foreman_port)

        self._generate_foreman_config()

    def _generate_foreman_config(self)
        template_context = {
            'FOREMAN_HOST': self._get_cloud_config('foreman_host'),
            'FOREMAN_PORT': self._get_cloud_config('foreman_port'),
        }

        foreman_config_template = self._read_config_template()
        foreman_config = self._populate_config_template(
            foreman_config_template,
            template_context,
        )
        self._write_config(foreman_config)

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
        env['foreman_host'] = self._get_cloud_config('foreman_host')
        env['foreman_port'] = self._get_cloud_config('foreman_port')
