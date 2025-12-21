from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os
from ansible.plugins.action import ActionBase
from ansible.utils.display import Display

display = Display()

class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)
        del tmp  # tmp no longer has any effect

        # Locate the PHP files on the controller
        # This file is in plugins/action/
        # We need plugins/module_utils/php/

        # Helper to find the collection root or relative path
        # If installed via galaxy, this file is in .../plugins/action/record.py
        # We want .../plugins/module_utils/php/

        current_dir = os.path.dirname(os.path.realpath(__file__))
        # Go up one level to plugins, then to module_utils/php
        php_utils_dir = os.path.join(os.path.dirname(current_dir), 'module_utils', 'php')

        wrapper_path = os.path.join(php_utils_dir, 'cloudns_wrapper.php')
        sdk_path = os.path.join(php_utils_dir, 'ClouDNS_SDK.php')

        if not os.path.exists(wrapper_path) or not os.path.exists(sdk_path):
             result['failed'] = True
             result['msg'] = "Could not find PHP files at {}. Ensure the collection is installed correctly.".format(php_utils_dir)
             return result

        try:
            with open(wrapper_path, 'r') as f:
                wrapper_content = f.read()
            with open(sdk_path, 'r') as f:
                sdk_content = f.read()
        except Exception as e:
            result['failed'] = True
            result['msg'] = "Failed to read PHP files: {}".format(str(e))
            return result

        # Inject content into module args
        module_args = self._task.args.copy()
        module_args['_wrapper_content'] = wrapper_content
        module_args['_sdk_content'] = sdk_content

        # Execute the module
        result = self._execute_module(
            module_name='host_uk.cloudns.record',
            module_args=module_args,
            task_vars=task_vars,
            wrap_async=self._task.async_val
        )

        return result
