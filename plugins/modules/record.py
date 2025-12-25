#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Jules
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: record
short_description: Manage ClouDNS DNS records
description:
  - Manage ClouDNS DNS records using direct API calls via Swagger/OpenAPI.
  - Uses pure Python HTTP client for API communication.
  - Legacy PHP mode is still supported for backward compatibility.
version_added: "1.1.0"
options:
  auth_id:
    description:
      - The API ID (or sub-user ID).
    required: true
    type: str
  auth_password:
    description:
      - The API password.
    required: true
    type: str
  sub_auth_user:
    description:
      - Set to true if using a sub-user account (ID or username).
    type: bool
    default: false
  domain:
    description:
      - The domain name.
    required: true
    type: str
  host:
    description:
      - The host name (e.g. www, @).
    default: ''
    type: str
  type:
    description:
      - The record type (A, AAAA, TXT, CNAME, MX, NS, SRV, CAA, etc).
    required: true
    type: str
    choices:
      - A
      - AAAA
      - MX
      - CNAME
      - TXT
      - NS
      - SRV
      - WR
      - RP
      - SSHFP
      - ALIAS
      - CAA
      - TLSA
      - CERT
      - DS
      - PTR
      - NAPTR
      - HINFO
      - LOC
      - SPF
  value:
    description:
      - The record value (IP, text, etc).
      - Required when state is 'present'.
    required: false
    type: str
  ttl:
    description:
      - The TTL value in seconds.
    default: 3600
    type: int
  priority:
    description:
      - Record priority (for MX, SRV records).
    type: int
    required: false
  weight:
    description:
      - Record weight (for SRV records).
    type: int
    required: false
  port:
    description:
      - Port number (for SRV records).
    type: int
    required: false
  state:
    description:
      - Whether the record should be present or absent.
    choices: [ present, absent ]
    default: present
    type: str
  verify_ssl:
    description:
      - Whether to verify SSL certificates when connecting to API.
    type: bool
    default: true
  timeout:
    description:
      - API request timeout in seconds.
    type: int
    default: 30
  use_php:
    description:
      - Use legacy PHP execution mode instead of native Python.
      - Set to true for backward compatibility with PHP-based execution.
    type: bool
    default: false
  use_docker:
    description:
      - Whether to use Docker to run the PHP script (only when use_php is true).
      - If true, Docker must be installed on the target machine.
    type: bool
    default: false
  docker_image:
    description:
      - The Docker image to use when use_docker is true.
    type: str
    default: php:cli
  _wrapper_content:
    description:
      - Internal use only. PHP wrapper content for legacy mode.
    type: str
    required: false
  _sdk_content:
    description:
      - Internal use only. PHP SDK content for legacy mode.
    type: str
    required: false
requirements:
  - Python 2.7 or higher
  - For use_php mode only: PHP with curl extension
notes:
  - This module uses a Python-based Swagger client by default, requiring no PHP installation.
  - The Swagger client can be reused in other Ansible modules/collections.
  - Set use_php=true to use the legacy PHP-based execution for backward compatibility.
author:
  - "Jules (@jules)"
'''

EXAMPLES = r'''
# Using native Python client (default, recommended)
- name: Add A record
  host_uk.cloudns.record:
    auth_id: "1234"
    auth_password: "secretpassword"
    domain: example.com
    host: www
    type: A
    value: 1.2.3.4

- name: Add MX record with priority
  host_uk.cloudns.record:
    auth_id: "1234"
    auth_password: "secretpassword"
    domain: example.com
    host: "@"
    type: MX
    value: mail.example.com
    priority: 10

- name: Add SRV record
  host_uk.cloudns.record:
    auth_id: "1234"
    auth_password: "secretpassword"
    domain: example.com
    host: _sip._tcp
    type: SRV
    value: sipserver.example.com
    priority: 10
    weight: 20
    port: 5060
    ttl: 3600

- name: Delete a record
  host_uk.cloudns.record:
    auth_id: "1234"
    auth_password: "secretpassword"
    domain: example.com
    host: old
    type: A
    state: absent

- name: Add record with custom timeout
  host_uk.cloudns.record:
    auth_id: "1234"
    auth_password: "secretpassword"
    domain: example.com
    host: www
    type: A
    value: 1.2.3.4
    timeout: 60
    verify_ssl: true

# Using legacy PHP mode
- name: Add A record using legacy PHP
  host_uk.cloudns.record:
    auth_id: "1234"
    auth_password: "secretpassword"
    domain: example.com
    host: www
    type: A
    value: 1.2.3.4
    use_php: true

- name: Add record using Docker (PHP mode)
  host_uk.cloudns.record:
    auth_id: "1234"
    auth_password: "secretpassword"
    domain: example.com
    host: server1
    type: A
    value: 10.0.0.1
    use_php: true
    use_docker: true
    docker_image: php:8.2-cli
'''

RETURN = r'''
changed:
    description: Whether the record was changed.
    type: bool
    returned: always
msg:
    description: Description of what happened.
    type: str
    returned: always
data:
    description: The data returned from the API (on changes).
    type: dict
    returned: when changed
record:
    description: Details of the record that was managed.
    type: dict
    returned: always
    contains:
        domain:
            description: The domain name.
            type: str
        host:
            description: The host name.
            type: str
        type:
            description: The record type.
            type: str
        value:
            description: The record value.
            type: str
        ttl:
            description: The TTL value.
            type: int
'''

import json
import os
import subprocess
import shutil
from ansible.module_utils.basic import AnsibleModule


def run_with_swagger_client(module):
    """Execute using the native Python Swagger client."""
    try:
        # Import the ClouDNS API client
        from ansible_collections.host_uk.cloudns.plugins.module_utils.swagger.cloudns_api import (
            ClouDNSClient,
            ClouDNSError,
        )
    except ImportError as e:
        module.fail_json(
            msg="Failed to import ClouDNS Swagger client. "
            "Ensure the collection is properly installed. Error: {}".format(str(e))
        )

    # Extract parameters
    auth_id = module.params['auth_id']
    auth_password = module.params['auth_password']
    is_subuser = module.params['sub_auth_user']
    domain = module.params['domain']
    host = module.params['host']
    record_type = module.params['type']
    value = module.params.get('value')
    ttl = module.params['ttl']
    state = module.params['state']
    verify_ssl = module.params['verify_ssl']
    timeout = module.params['timeout']

    # Optional record parameters
    priority = module.params.get('priority')
    weight = module.params.get('weight')
    port = module.params.get('port')

    try:
        # Create the client
        client = ClouDNSClient(
            auth_id=auth_id,
            auth_password=auth_password,
            is_subuser=is_subuser,
            timeout=timeout,
            verify_ssl=verify_ssl,
        )

        # Build extra kwargs for special record types
        extra_params = {}
        if priority is not None:
            extra_params['priority'] = priority
        if weight is not None:
            extra_params['weight'] = weight
        if port is not None:
            extra_params['port'] = port

        # Use the ensure_record method for idempotent operation
        result = client.ensure_record(
            domain_name=domain,
            host=host,
            record_type=record_type,
            value=value,
            ttl=ttl,
            state=state,
            **extra_params
        )

        # Add record info to result
        result['record'] = {
            'domain': domain,
            'host': host,
            'type': record_type,
            'value': value,
            'ttl': ttl,
        }

        if result.get('failed'):
            module.fail_json(**result)
        else:
            module.exit_json(**result)

    except ClouDNSError as e:
        module.fail_json(
            msg="ClouDNS API error: {}".format(str(e)),
            record={
                'domain': domain,
                'host': host,
                'type': record_type,
            }
        )
    except Exception as e:
        module.fail_json(
            msg="Unexpected error: {}".format(str(e)),
            record={
                'domain': domain,
                'host': host,
                'type': record_type,
            }
        )


def run_with_php(module):
    """Execute using legacy PHP mode."""
    use_docker = module.params['use_docker']
    docker_image = module.params['docker_image']
    wrapper_content = module.params.get('_wrapper_content')
    sdk_content = module.params.get('_sdk_content')

    if not wrapper_content or not sdk_content:
        module.fail_json(
            msg="PHP module content missing. When using use_php=true, "
            "this module must be run via the corresponding Action Plugin."
        )

    import tempfile

    class TemporaryDirectory(object):
        def __init__(self):
            self.name = tempfile.mkdtemp()

        def __enter__(self):
            return self.name

        def __exit__(self, exc_type, exc_value, traceback):
            shutil.rmtree(self.name)

    with TemporaryDirectory() as temp_dir:
        # Write files
        wrapper_path = os.path.join(temp_dir, 'cloudns_wrapper.php')
        sdk_path = os.path.join(temp_dir, 'ClouDNS_SDK.php')

        with open(wrapper_path, 'w') as f:
            f.write(wrapper_content)
        with open(sdk_path, 'w') as f:
            f.write(sdk_content)

        # Prepare command
        cmd = []
        if use_docker:
            try:
                subprocess.check_call(
                    ['docker', '--version'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            except subprocess.CalledProcessError:
                module.fail_json(
                    msg="Docker check failed. Ensure Docker is installed and running."
                )
            except OSError:
                module.fail_json(msg="Docker binary not found in PATH.")

            cmd = [
                'docker', 'run', '--rm', '-i',
                '-v', '{}:/app'.format(temp_dir),
                '-w', '/app',
                docker_image,
                'php', 'cloudns_wrapper.php'
            ]
        else:
            try:
                subprocess.check_call(
                    ['php', '-v'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            except subprocess.CalledProcessError:
                module.fail_json(msg="PHP check failed. Ensure PHP is working.")
            except OSError:
                module.fail_json(
                    msg="PHP binary not found in PATH. "
                    "Install PHP or set use_php: false to use native Python client."
                )

            cmd = ['php', wrapper_path]

        # Prepare input
        payload = module.params.copy()
        payload.pop('_wrapper_content', None)
        payload.pop('_sdk_content', None)
        payload['action'] = 'ensure_record'

        input_json = json.dumps(payload)

        # Execute
        try:
            rc, stdout, stderr = module.run_command(cmd, data=input_json, binary_data=False)

            if rc != 0:
                safe_stderr = stderr
                if module.params['auth_password'] in safe_stderr:
                    safe_stderr = safe_stderr.replace(
                        module.params['auth_password'], '********'
                    )
                module.fail_json(
                    msg="Script execution failed with error code " + str(rc),
                    stderr=safe_stderr,
                    stdout=stdout
                )

            try:
                result = json.loads(stdout)
            except ValueError:
                module.fail_json(
                    msg="Failed to parse JSON response from script",
                    output=stdout,
                    stderr=stderr
                )

            if result.get('failed'):
                module.fail_json(msg=result.get('msg', 'Unknown error'), **result)

            module.exit_json(**result)

        except Exception as e:
            module.fail_json(msg="Exception while running script: " + str(e))


def main():
    module = AnsibleModule(
        argument_spec=dict(
            # Authentication
            auth_id=dict(type='str', required=True),
            auth_password=dict(type='str', required=True, no_log=True),
            sub_auth_user=dict(type='bool', default=False),

            # Record parameters
            domain=dict(type='str', required=True),
            host=dict(type='str', default=''),
            type=dict(
                type='str',
                required=True,
                choices=[
                    'A', 'AAAA', 'MX', 'CNAME', 'TXT', 'NS', 'SRV', 'WR',
                    'RP', 'SSHFP', 'ALIAS', 'CAA', 'TLSA', 'CERT', 'DS',
                    'PTR', 'NAPTR', 'HINFO', 'LOC', 'SPF'
                ]
            ),
            value=dict(type='str', required=False),
            ttl=dict(type='int', default=3600),
            state=dict(type='str', default='present', choices=['present', 'absent']),

            # Optional record-type specific parameters
            priority=dict(type='int', required=False),
            weight=dict(type='int', required=False),
            port=dict(type='int', required=False),

            # Client options
            verify_ssl=dict(type='bool', default=True),
            timeout=dict(type='int', default=30),

            # Execution mode
            use_php=dict(type='bool', default=False),
            use_docker=dict(type='bool', default=False),
            docker_image=dict(type='str', default='php:cli'),

            # Hidden args injected by Action Plugin (for PHP mode)
            _wrapper_content=dict(type='str', required=False, no_log=True),
            _sdk_content=dict(type='str', required=False, no_log=True),
        ),
        required_if=[
            ('state', 'present', ('value',)),
            ('use_php', True, ()),  # PHP mode has additional requirements handled in run_with_php
        ],
        supports_check_mode=False
    )

    # Determine execution mode
    use_php = module.params['use_php']

    if use_php:
        run_with_php(module)
    else:
        run_with_swagger_client(module)


if __name__ == '__main__':
    main()
