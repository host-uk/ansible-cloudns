#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: record
short_description: Manage ClouDNS DNS records
description:
  - Manage ClouDNS DNS records using the PHP SDK.
  - Can run PHP locally or via Docker.
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
      - The record type (A, AAAA, TXT, etc).
    required: true
    type: str
  value:
    description:
      - The record value (IP, text, etc).
    required: false
    type: str
  ttl:
    description:
      - The TTL value.
    default: 3600
    type: int
  state:
    description:
      - Whether the record should be present or absent.
    choices: [ present, absent ]
    default: present
    type: str
  use_docker:
    description:
      - Whether to use Docker to run the PHP script.
      - If true, Docker must be installed on the target machine.
    type: bool
    default: false
  docker_image:
    description:
      - The Docker image to use when use_docker is true.
    type: str
    default: php:cli
author:
  - "Jules"
'''

EXAMPLES = r'''
- name: Add A record using local PHP
  cloudns.cloudns.record:
    auth_id: 1234
    auth_password: "secretpassword"
    domain: example.com
    host: www
    type: A
    value: 1.2.3.4

- name: Update IP using Docker
  cloudns.cloudns.record:
    auth_id: 1234
    auth_password: "secretpassword"
    domain: example.com
    host: server1
    type: A
    value: 10.0.0.1
    use_docker: true
    docker_image: php:8.2-cli
'''

RETURN = r'''
msg:
    description: The message returned from the PHP wrapper.
    type: str
    returned: always
data:
    description: The data returned from the API.
    type: dict
    returned: when changed
'''

import json
import os
import subprocess
import tempfile
import shutil
from ansible.module_utils.basic import AnsibleModule

def main():
    module = AnsibleModule(
        argument_spec=dict(
            auth_id=dict(type='str', required=True),
            auth_password=dict(type='str', required=True, no_log=True),
            sub_auth_user=dict(type='bool', default=False),
            domain=dict(type='str', required=True),
            host=dict(type='str', default=''),
            type=dict(type='str', required=True),
            value=dict(type='str', required=False),
            ttl=dict(type='int', default=3600),
            state=dict(type='str', default='present', choices=['present', 'absent']),
            use_docker=dict(type='bool', default=False),
            docker_image=dict(type='str', default='php:cli'),
            # Hidden args injected by Action Plugin
            _wrapper_content=dict(type='str', required=False),
            _sdk_content=dict(type='str', required=False),
        ),
        required_if=[
            ('state', 'present', ('value',))
        ],
        supports_check_mode=False
    )

    use_docker = module.params['use_docker']
    docker_image = module.params['docker_image']
    wrapper_content = module.params.get('_wrapper_content')
    sdk_content = module.params.get('_sdk_content')

    if not wrapper_content or not sdk_content:
        module.fail_json(msg="PHP module content missing. This module must be run via the corresponding Action Plugin.")

    # Create temporary directory
    temp_dir = tempfile.mkdtemp()

    try:
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
            # Check if Docker is installed
            try:
                subprocess.check_output(['docker', '--version'])
            except OSError:
                module.fail_json(msg="Docker is not installed or not in PATH.")

            # Mount temp_dir to /app
            # If using Docker on remote host, temp_dir is on remote host.
            # Docker requires absolute paths.

            # Note: On some systems/setups (e.g. Docker inside Docker, or specialized SELinux), mounting /tmp might have issues.
            # But standard usage allows this.

            cmd = [
                'docker', 'run', '--rm', '-i',
                '-v', '{}:/app'.format(temp_dir),
                '-w', '/app',
                docker_image,
                'php', 'cloudns_wrapper.php'
            ]
        else:
            # Check if php is installed
            try:
                subprocess.check_output(['php', '-v'])
            except OSError:
                module.fail_json(msg="PHP is not installed or not in PATH. Install PHP or set use_docker: true")

            cmd = ['php', wrapper_path]

        # Prepare input
        payload = module.params.copy()
        # Remove hidden args from payload sent to PHP to avoid overhead/confusion (PHP script doesn't read them, but good hygiene)
        payload.pop('_wrapper_content', None)
        payload.pop('_sdk_content', None)
        payload['action'] = 'ensure_record'

        input_json = json.dumps(payload)

        # Execute
        try:
            p = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = p.communicate(input=input_json.encode('utf-8'))

            if p.returncode != 0:
                module.fail_json(msg="Script execution failed with error code " + str(p.returncode), stderr=stderr.decode('utf-8'), stdout=stdout.decode('utf-8'))

            # Parse output
            try:
                result = json.loads(stdout.decode('utf-8'))
            except ValueError:
                module.fail_json(msg="Failed to parse JSON response from script", output=stdout.decode('utf-8'), stderr=stderr.decode('utf-8'))

            if result.get('failed'):
                module.fail_json(msg=result.get('msg', 'Unknown error'), **result)

            module.exit_json(**result)

        except Exception as e:
            module.fail_json(msg="Exception while running script: " + str(e))

    finally:
        shutil.rmtree(temp_dir)

if __name__ == '__main__':
    main()
