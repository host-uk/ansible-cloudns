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
  - Requires PHP to be installed on the target machine (or localhost if using connection: local).
options:
  auth_id:
    description:
      - The API ID (or sub-user ID).
    required: true
    type: int
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
author:
  - "Jules"
'''

EXAMPLES = r'''
- name: Add A record
  cloudns.cloudns.record:
    auth_id: 1234
    auth_password: "secretpassword"
    domain: example.com
    host: www
    type: A
    value: 1.2.3.4

- name: Update IP
  cloudns.cloudns.record:
    auth_id: 1234
    auth_password: "secretpassword"
    domain: example.com
    host: server1
    type: A
    value: 10.0.0.1
    state: present
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
        ),
        required_if=[
            ('state', 'present', ('value',))
        ],
        supports_check_mode=False
    )

    # Locate the PHP wrapper
    # We assume the wrapper is in ../module_utils/php/cloudns_wrapper.php relative to this file
    # Or in the same directory if flattened?
    # In a collection, plugins/modules/record.py
    # and plugins/module_utils/php/cloudns_wrapper.php

    # When running from installed collection, the structure is preserved.
    module_dir = os.path.dirname(os.path.realpath(__file__))
    # Go up two levels: plugins/modules -> plugins -> module_utils
    # Wait, module_dir is .../plugins/modules
    # We need .../plugins/module_utils/php/cloudns_wrapper.php

    # Standard path in collection
    wrapper_path = os.path.join(module_dir, '../../module_utils/php/cloudns_wrapper.php')
    sdk_path = os.path.join(module_dir, '../../module_utils/php/ClouDNS_SDK.php')

    # Normalize path
    wrapper_path = os.path.normpath(wrapper_path)
    sdk_path = os.path.normpath(sdk_path)

    if not os.path.exists(wrapper_path):
        module.fail_json(msg="Could not find PHP wrapper at " + wrapper_path)

    # Check if php is installed
    try:
        subprocess.check_output(['php', '-v'])
    except OSError:
        module.fail_json(msg="PHP is not installed or not in PATH.")

    # Prepare input
    payload = module.params.copy()
    payload['action'] = 'ensure_record'

    input_json = json.dumps(payload)

    # Execute PHP wrapper
    try:
        p = subprocess.Popen(
            ['php', wrapper_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = p.communicate(input=input_json.encode('utf-8'))

        if p.returncode != 0:
            module.fail_json(msg="PHP script failed with error code " + str(p.returncode), stderr=stderr.decode('utf-8'), stdout=stdout.decode('utf-8'))

        # Parse output
        try:
            result = json.loads(stdout.decode('utf-8'))
        except ValueError:
            module.fail_json(msg="Failed to parse JSON response from PHP script", output=stdout.decode('utf-8'), stderr=stderr.decode('utf-8'))

        if result.get('failed'):
            module.fail_json(msg=result.get('msg', 'Unknown error'), **result)

        module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg="Exception while running PHP wrapper: " + str(e))

if __name__ == '__main__':
    main()
