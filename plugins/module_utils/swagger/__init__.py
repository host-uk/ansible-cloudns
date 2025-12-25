# -*- coding: utf-8 -*-
# Copyright: (c) 2024, ClouDNS Ansible Collection
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Swagger/OpenAPI utilities for Ansible modules.

This package provides reusable components for interacting with REST APIs
using OpenAPI/Swagger specifications.

Components:
    - swagger_client: Generic OpenAPI client (reusable for any API)
    - cloudns_api: ClouDNS-specific API client

Usage:
    # For ClouDNS
    from ansible_collections.host_uk.cloudns.plugins.module_utils.swagger.cloudns_api import (
        ClouDNSClient,
        ClouDNSError,
    )

    # For generic Swagger/OpenAPI
    from ansible_collections.host_uk.cloudns.plugins.module_utils.swagger.swagger_client import (
        SwaggerClient,
        SwaggerClientBuilder,
        load_swagger_spec,
    )
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type
