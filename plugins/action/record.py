from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os
from ansible.plugins.action import ActionBase
from ansible.utils.display import Display

display = Display()


class ActionModule(ActionBase):
    """
    Action plugin for the host_uk.cloudns.record module.

    This plugin handles two execution modes:
    1. Native Python mode (default): Passes through to the module which uses
       the Swagger client directly. No PHP files needed.
    2. Legacy PHP mode (use_php=true): Injects PHP wrapper and SDK content
       into the module args for PHP-based execution.
    """

    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)
        del tmp  # tmp no longer has any effect

        module_args = self._task.args.copy()

        # Check if PHP mode is requested
        use_php = module_args.get('use_php', False)

        if use_php:
            # Legacy PHP mode: inject PHP files
            result = self._inject_php_content(result, module_args)
            if result.get('failed'):
                return result

        # Execute the module
        result = self._execute_module(
            module_name='host_uk.cloudns.record',
            module_args=module_args,
            task_vars=task_vars,
            wrap_async=self._task.async_val
        )

        return result

    def _inject_php_content(self, result, module_args):
        """
        Inject PHP wrapper and SDK content into module args for legacy PHP mode.

        Args:
            result: The result dict to update on failure
            module_args: The module args dict to inject content into

        Returns:
            result dict (may have 'failed' set on error)
        """
        # Locate the PHP files on the controller
        # This file is in plugins/action/
        # We need plugins/module_utils/php/

        current_dir = os.path.dirname(os.path.realpath(__file__))
        # Go up one level to plugins, then to module_utils/php
        php_utils_dir = os.path.realpath(
            os.path.join(os.path.dirname(current_dir), 'module_utils', 'php')
        )

        wrapper_path = os.path.realpath(
            os.path.join(php_utils_dir, 'cloudns_wrapper.php')
        )
        sdk_path = os.path.realpath(
            os.path.join(php_utils_dir, 'ClouDNS_SDK.php')
        )

        # Ensure resolved paths stay within the expected php_utils_dir
        for candidate, label in (
            (wrapper_path, 'cloudns_wrapper.php'),
            (sdk_path, 'ClouDNS_SDK.php')
        ):
            if not candidate.startswith(php_utils_dir + os.sep):
                result['failed'] = True
                result['msg'] = (
                    "Resolved path for {} is outside the expected directory {}"
                    .format(label, php_utils_dir)
                )
                return result

        if not os.path.exists(wrapper_path) or not os.path.exists(sdk_path):
            result['failed'] = True
            result['msg'] = (
                "Could not find PHP files at {}. "
                "Ensure the collection is installed correctly. "
                "Alternatively, set use_php: false to use the native Python client."
                .format(php_utils_dir)
            )
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
        module_args['_wrapper_content'] = wrapper_content
        module_args['_sdk_content'] = sdk_content

        return result
