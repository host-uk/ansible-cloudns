# -*- coding: utf-8 -*-
# Copyright: (c) 2024, ClouDNS Ansible Collection
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
ClouDNS API Client using Swagger/OpenAPI specification.

This module provides a high-level interface to the ClouDNS API using the
generic SwaggerClient. It handles authentication, response parsing, and
provides convenience methods for common DNS operations.

Usage:
    from ansible_collections.host_uk.cloudns.plugins.module_utils.swagger.cloudns_api import (
        ClouDNSClient,
        ClouDNSError,
    )

    # Create client
    client = ClouDNSClient(
        auth_id='12345',
        auth_password='secret',
        is_subuser=False,
    )

    # List records
    records = client.list_records('example.com')

    # Add record
    result = client.add_record(
        domain='example.com',
        record_type='A',
        host='www',
        value='192.168.1.1',
        ttl=3600,
    )
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import os
from .swagger_client import SwaggerClient, SwaggerClientError, load_swagger_spec


class ClouDNSError(Exception):
    """Exception raised by ClouDNS operations."""

    def __init__(self, message, api_response=None):
        super(ClouDNSError, self).__init__(message)
        self.api_response = api_response


def get_swagger_spec_path():
    """Get the path to the ClouDNS swagger spec file."""
    return os.path.join(os.path.dirname(__file__), 'cloudns_swagger.json')


class ClouDNSClient:
    """
    ClouDNS API client using Swagger specification.

    This client provides a Pythonic interface to the ClouDNS API, handling
    authentication and providing convenience methods for DNS operations.
    """

    API_BASE_URL = 'https://api.cloudns.net'

    def __init__(
        self,
        auth_id,
        auth_password,
        is_subuser=False,
        timeout=30,
        verify_ssl=True,
        max_retries=3,
        spec_path=None,
    ):
        """
        Initialize the ClouDNS client.

        Args:
            auth_id: API auth ID or sub-user ID/username
            auth_password: API password
            is_subuser: True if using sub-user authentication
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
            max_retries: Maximum retry attempts for failed requests
            spec_path: Optional path to swagger spec file
        """
        self.auth_id = auth_id
        self.auth_password = auth_password
        self.is_subuser = is_subuser

        # Determine auth type
        if not is_subuser:
            self.auth_type = 'auth-id'
        else:
            # Sub-users can use ID (numeric) or username
            if str(auth_id).isdigit():
                self.auth_type = 'sub-auth-id'
            else:
                self.auth_type = 'sub-auth-user'

        # Build auth parameters
        self.auth_params = {
            self.auth_type: auth_id,
            'auth-password': auth_password,
        }

        # Load swagger spec
        spec_path = spec_path or get_swagger_spec_path()
        spec = load_swagger_spec(spec_path)

        # Create swagger client
        self._client = SwaggerClient(
            spec=spec,
            base_url=self.API_BASE_URL,
            auth_params=self.auth_params,
            timeout=timeout,
            verify_ssl=verify_ssl,
            max_retries=max_retries,
        )

    def _check_response(self, response, operation_name):
        """Check API response for errors."""
        if isinstance(response, dict):
            status = response.get('status')
            if status == 'Failed' or status == 'failed':
                message = response.get('statusDescription') or response.get('message', 'Unknown error')
                raise ClouDNSError(f"{operation_name} failed: {message}", response)
        return response

    def _call(self, operation_id, params=None, check_response=True):
        """Call an API operation and optionally check for errors."""
        try:
            response = self._client.call_operation(operation_id, params)
            if check_response:
                return self._check_response(response, operation_id)
            return response
        except SwaggerClientError as e:
            raise ClouDNSError(str(e))

    # =========================================================================
    # Authentication
    # =========================================================================

    def login(self):
        """
        Verify API credentials.

        Returns:
            dict: API response with login status

        Raises:
            ClouDNSError: If authentication fails
        """
        return self._call('apiLogin')

    # =========================================================================
    # Zone Management
    # =========================================================================

    def register_zone(self, domain_name, zone_type, ns=None, master_ip=None):
        """
        Register a new DNS zone.

        Args:
            domain_name: The domain name
            zone_type: Type of zone (master, slave, parked, geodns)
            ns: List of nameservers (optional)
            master_ip: Master IP for slave zones

        Returns:
            dict: API response
        """
        params = {
            'domain-name': domain_name,
            'zone-type': zone_type,
        }
        if ns:
            params['ns[]'] = ns
        if master_ip:
            params['master-ip'] = master_ip

        return self._call('dnsRegisterDomainZone', params)

    def delete_zone(self, domain_name):
        """
        Delete a DNS zone.

        Args:
            domain_name: The domain name to delete

        Returns:
            dict: API response
        """
        return self._call('dnsDeleteDomainZone', {'domain-name': domain_name})

    def list_zones(self, page=1, rows_per_page=20, search=None, group_id=None):
        """
        List DNS zones.

        Args:
            page: Page number
            rows_per_page: Number of rows per page
            search: Search term
            group_id: Filter by group ID

        Returns:
            dict: List of zones
        """
        params = {
            'page': page,
            'rows-per-page': rows_per_page,
        }
        if search:
            params['search'] = search
        if group_id:
            params['group-id'] = group_id

        return self._call('dnsListZones', params, check_response=False)

    def get_zone_info(self, domain_name):
        """
        Get zone information.

        Args:
            domain_name: The domain name

        Returns:
            dict: Zone information
        """
        return self._call('dnsGetZoneInformation', {'domain-name': domain_name})

    def update_zone(self, domain_name):
        """
        Trigger zone update/reload.

        Args:
            domain_name: The domain name

        Returns:
            dict: API response
        """
        return self._call('dnsUpdateZone', {'domain-name': domain_name})

    def get_available_nameservers(self):
        """
        Get available nameservers.

        Returns:
            list: Available nameservers
        """
        return self._call('dnsAvailableNameServers', check_response=False)

    # =========================================================================
    # DNS Records
    # =========================================================================

    def list_records(self, domain_name, host=None, record_type=None):
        """
        List DNS records for a domain.

        Args:
            domain_name: The domain name
            host: Filter by host (optional)
            record_type: Filter by record type (optional)

        Returns:
            dict: Dictionary of records keyed by record ID
        """
        params = {'domain-name': domain_name}
        if host is not None:
            params['host'] = host
        if record_type:
            params['type'] = record_type

        response = self._call('dnsListRecords', params, check_response=False)

        # Handle "no records" response
        if isinstance(response, dict):
            status = response.get('status')
            if status == 'Failed':
                desc = response.get('statusDescription', '')
                # "No records" is not an error, just empty result
                if 'no record' in desc.lower() or 'not found' in desc.lower():
                    return {}
                raise ClouDNSError(f"List records failed: {desc}", response)

        return response if response else {}

    def add_record(
        self,
        domain_name,
        record_type,
        host,
        value,
        ttl,
        priority=None,
        weight=None,
        port=None,
        frame=None,
        frame_title=None,
        frame_keywords=None,
        frame_description=None,
        save_path=None,
        redirect_type=None,
        mail=None,
        txt=None,
        algorithm=None,
        fptype=None,
        status=1,
        geodns_location=None,
        caa_flag=None,
        caa_type=None,
        caa_value=None,
        mobile_meta=None,
        tlsa_usage=None,
        tlsa_selector=None,
        tlsa_matching_type=None,
        key_tag=None,
        digest_type=None,
        order=None,
        pref=None,
        flag=None,
        params=None,
        regexp=None,
        replace=None,
        cert_type=None,
        cert_key_tag=None,
        cert_algorithm=None,
        lat_deg=None,
        lat_min=None,
        lat_sec=None,
        lat_dir=None,
        long_deg=None,
        long_min=None,
        long_sec=None,
        long_dir=None,
        altitude=None,
        size=None,
        h_precision=None,
        v_precision=None,
        cpu=None,
        os=None,
    ):
        """
        Add a DNS record.

        Args:
            domain_name: The domain name
            record_type: Record type (A, AAAA, CNAME, MX, TXT, etc.)
            host: Host name (@ for root, www, etc.)
            value: Record value (IP address, hostname, etc.)
            ttl: Time to live in seconds
            priority: Priority for MX/SRV records
            weight: Weight for SRV records
            port: Port for SRV records
            ... (additional record-type specific parameters)

        Returns:
            dict: API response with status
        """
        api_params = {
            'domain-name': domain_name,
            'record-type': record_type,
            'host': host,
            'record': value,
            'ttl': ttl,
        }

        # Add optional parameters
        optional_params = {
            'priority': priority,
            'weight': weight,
            'port': port,
            'frame': frame,
            'frame-title': frame_title,
            'frame-keywords': frame_keywords,
            'frame-description': frame_description,
            'save-path': save_path,
            'redirect-type': redirect_type,
            'mail': mail,
            'txt': txt,
            'algorithm': algorithm,
            'fptype': fptype,
            'status': status,
            'geodns-location': geodns_location,
            'caa_flag': caa_flag,
            'caa_type': caa_type,
            'caa_value': caa_value,
            'mobile-meta': mobile_meta,
            'tlsa_usage': tlsa_usage,
            'tlsa_selector': tlsa_selector,
            'tlsa_matching_type': tlsa_matching_type,
            'key-tag': key_tag,
            'digest-type': digest_type,
            'order': order,
            'pref': pref,
            'flag': flag,
            'params': params,
            'regexp': regexp,
            'replace': replace,
            'cert-type': cert_type,
            'cert-key-tag': cert_key_tag,
            'cert-algorithm': cert_algorithm,
            'lat-deg': lat_deg,
            'lat-min': lat_min,
            'lat-sec': lat_sec,
            'lat-dir': lat_dir,
            'long-deg': long_deg,
            'long-min': long_min,
            'long-sec': long_sec,
            'long-dir': long_dir,
            'altitude': altitude,
            'size': size,
            'h-precision': h_precision,
            'v-precision': v_precision,
            'cpu': cpu,
            'os': os,
        }

        for key, val in optional_params.items():
            if val is not None:
                api_params[key] = val

        return self._call('dnsAddRecord', api_params)

    def modify_record(
        self,
        domain_name,
        record_id,
        host,
        value,
        ttl,
        priority=None,
        weight=None,
        port=None,
        frame=None,
        frame_title=None,
        frame_keywords=None,
        frame_description=None,
        save_path=None,
        redirect_type=None,
        mail=None,
        txt=None,
        algorithm=None,
        fptype=None,
        status=None,
        geodns_location=None,
        caa_flag=None,
        caa_type=None,
        caa_value=None,
        **kwargs
    ):
        """
        Modify an existing DNS record.

        Args:
            domain_name: The domain name
            record_id: ID of the record to modify
            host: Host name
            value: New record value
            ttl: New TTL value
            ... (additional optional parameters)

        Returns:
            dict: API response
        """
        api_params = {
            'domain-name': domain_name,
            'record-id': record_id,
            'host': host,
            'record': value,
            'ttl': ttl,
        }

        optional_params = {
            'priority': priority,
            'weight': weight,
            'port': port,
            'frame': frame,
            'frame-title': frame_title,
            'frame-keywords': frame_keywords,
            'frame-description': frame_description,
            'save-path': save_path,
            'redirect-type': redirect_type,
            'mail': mail,
            'txt': txt,
            'algorithm': algorithm,
            'fptype': fptype,
            'status': status,
            'geodns-location': geodns_location,
            'caa_flag': caa_flag,
            'caa_type': caa_type,
            'caa_value': caa_value,
        }

        for key, val in optional_params.items():
            if val is not None:
                api_params[key] = val

        # Add any extra kwargs
        for key, val in kwargs.items():
            if val is not None:
                api_params[key.replace('_', '-')] = val

        return self._call('dnsModifyRecord', api_params)

    def delete_record(self, domain_name, record_id):
        """
        Delete a DNS record.

        Args:
            domain_name: The domain name
            record_id: ID of the record to delete

        Returns:
            dict: API response
        """
        return self._call('dnsDeleteRecord', {
            'domain-name': domain_name,
            'record-id': record_id,
        })

    def get_available_record_types(self, zone_type='master'):
        """
        Get available record types for a zone type.

        Args:
            zone_type: The zone type

        Returns:
            list: Available record types
        """
        return self._call('dnsGetAvailableRecords', {'zone-type': zone_type}, check_response=False)

    def get_available_ttl(self):
        """
        Get available TTL values.

        Returns:
            list: Available TTL values
        """
        return self._call('dnsGetAvailableTTL', check_response=False)

    def copy_records(self, domain_name, from_domain, delete_current=False):
        """
        Copy records from another domain.

        Args:
            domain_name: Target domain
            from_domain: Source domain
            delete_current: Delete current records before copying

        Returns:
            dict: API response
        """
        return self._call('dnsCopyRecords', {
            'domain-name': domain_name,
            'from-domain': from_domain,
            'delete-current-records': 1 if delete_current else 0,
        })

    def export_records_bind(self, domain_name):
        """
        Export records in BIND format.

        Args:
            domain_name: The domain name

        Returns:
            dict: BIND zone file content
        """
        return self._call('dnsExportRecordsBIND', {'domain-name': domain_name})

    def import_records(self, domain_name, format, content, delete_existing=False):
        """
        Import records from BIND format.

        Args:
            domain_name: The domain name
            format: Import format (bind)
            content: Zone file content
            delete_existing: Delete existing records first

        Returns:
            dict: API response
        """
        return self._call('dnsImportRecords', {
            'domain-name': domain_name,
            'format': format,
            'content': content,
            'delete-existing-records': 1 if delete_existing else 0,
        })

    def change_record_status(self, domain_name, record_id, status):
        """
        Change record status (active/inactive).

        Args:
            domain_name: The domain name
            record_id: Record ID
            status: Status (1=active, 0=inactive)

        Returns:
            dict: API response
        """
        return self._call('dnsChangeRecordStatus', {
            'domain-name': domain_name,
            'record-id': record_id,
            'status': status,
        })

    # =========================================================================
    # SOA Records
    # =========================================================================

    def get_soa(self, domain_name):
        """
        Get SOA record details.

        Args:
            domain_name: The domain name

        Returns:
            dict: SOA record details
        """
        return self._call('dnsGetSOA', {'domain-name': domain_name})

    def modify_soa(
        self,
        domain_name,
        primary_ns,
        admin_mail,
        refresh,
        retry,
        expire,
        default_ttl,
    ):
        """
        Modify SOA record.

        Args:
            domain_name: The domain name
            primary_ns: Primary nameserver
            admin_mail: Admin email
            refresh: Refresh interval
            retry: Retry interval
            expire: Expire time
            default_ttl: Default TTL

        Returns:
            dict: API response
        """
        return self._call('dnsModifySOA', {
            'domain-name': domain_name,
            'primary-ns': primary_ns,
            'admin-mail': admin_mail,
            'refresh': refresh,
            'retry': retry,
            'expire': expire,
            'default-ttl': default_ttl,
        })

    # =========================================================================
    # Dynamic DNS
    # =========================================================================

    def get_dynamic_url(self, domain_name, record_id):
        """
        Get dynamic DNS URL for a record.

        Args:
            domain_name: The domain name
            record_id: Record ID

        Returns:
            dict: Dynamic URL info
        """
        return self._call('dnsGetDynamicURL', {
            'domain-name': domain_name,
            'record-id': record_id,
        })

    def disable_dynamic_url(self, domain_name, record_id):
        """
        Disable dynamic DNS URL.

        Args:
            domain_name: The domain name
            record_id: Record ID

        Returns:
            dict: API response
        """
        return self._call('dnsDisableDynamicURL', {
            'domain-name': domain_name,
            'record-id': record_id,
        })

    def change_dynamic_url(self, domain_name, record_id):
        """
        Change/regenerate dynamic DNS URL.

        Args:
            domain_name: The domain name
            record_id: Record ID

        Returns:
            dict: API response
        """
        return self._call('dnsChangeDynamicURL', {
            'domain-name': domain_name,
            'record-id': record_id,
        })

    # =========================================================================
    # Mail Forwards
    # =========================================================================

    def list_mail_forwards(self, domain_name):
        """
        List mail forwards for a domain.

        Args:
            domain_name: The domain name

        Returns:
            dict: Mail forwards
        """
        return self._call('dnsListMailForwards', {'domain-name': domain_name}, check_response=False)

    def add_mail_forward(self, domain_name, box, host, destination):
        """
        Add a mail forward.

        Args:
            domain_name: The domain name
            box: Mailbox name
            host: Host
            destination: Destination email

        Returns:
            dict: API response
        """
        return self._call('dnsAddMailForward', {
            'domain-name': domain_name,
            'box': box,
            'host': host,
            'destination': destination,
        })

    def delete_mail_forward(self, domain_name, mail_forward_id):
        """
        Delete a mail forward.

        Args:
            domain_name: The domain name
            mail_forward_id: Mail forward ID

        Returns:
            dict: API response
        """
        return self._call('dnsDeleteMailForward', {
            'domain-name': domain_name,
            'mail-forward-id': mail_forward_id,
        })

    def modify_mail_forward(self, domain_name, mail_forward_id, box, host, destination):
        """
        Modify a mail forward.

        Args:
            domain_name: The domain name
            mail_forward_id: Mail forward ID
            box: Mailbox name
            host: Host
            destination: Destination email

        Returns:
            dict: API response
        """
        return self._call('dnsModifyMailForward', {
            'domain-name': domain_name,
            'mail-forward-id': mail_forward_id,
            'box': box,
            'host': host,
            'destination': destination,
        })

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_hourly_statistics(self, domain_name, year, month, day):
        """Get hourly DNS statistics."""
        return self._call('dnsHourlyStatistics', {
            'domain-name': domain_name,
            'year': year,
            'month': month,
            'day': day,
        }, check_response=False)

    def get_daily_statistics(self, domain_name, year, month):
        """Get daily DNS statistics."""
        return self._call('dnsDailyStatistics', {
            'domain-name': domain_name,
            'year': year,
            'month': month,
        }, check_response=False)

    def get_monthly_statistics(self, domain_name, year):
        """Get monthly DNS statistics."""
        return self._call('dnsMonthlyStatistics', {
            'domain-name': domain_name,
            'year': year,
        }, check_response=False)

    def get_yearly_statistics(self, domain_name):
        """Get yearly DNS statistics."""
        return self._call('dnsYearlyStatistics', {
            'domain-name': domain_name,
        }, check_response=False)

    def get_last_30_days_statistics(self, domain_name):
        """Get last 30 days DNS statistics."""
        return self._call('dnsLast30DaysStatistics', {
            'domain-name': domain_name,
        }, check_response=False)

    # =========================================================================
    # Groups
    # =========================================================================

    def list_groups(self):
        """List domain groups."""
        return self._call('dnsListGroups', check_response=False)

    def add_group(self, domain_name, name):
        """Add a domain group."""
        return self._call('dnsAddGroup', {
            'domain-name': domain_name,
            'name': name,
        })

    def delete_group(self, group_id):
        """Delete a domain group."""
        return self._call('dnsDeleteGroup', {'group-id': group_id})

    def rename_group(self, group_id, new_name):
        """Rename a domain group."""
        return self._call('dnsRenameGroup', {
            'group-id': group_id,
            'new-name': new_name,
        })

    def change_group(self, domain_name, group_id):
        """Change domain's group."""
        return self._call('dnsChangeGroup', {
            'domain-name': domain_name,
            'group-id': group_id,
        })

    # =========================================================================
    # Sub Users
    # =========================================================================

    def list_sub_users(self, page=1, rows_per_page=20):
        """List sub-users."""
        return self._call('subListSubUsers', {
            'page': page,
            'rows-per-page': rows_per_page,
        }, check_response=False)

    def add_sub_user(self, password, zones, mail_forwards, ip=None):
        """Add a sub-user."""
        params = {
            'password': password,
            'zones': zones,
            'mail-forwards': mail_forwards,
        }
        if ip:
            params['ip'] = ip
        return self._call('subAddNewUser', params)

    def get_sub_user_info(self, user_id):
        """Get sub-user information."""
        return self._call('subGetUserInfo', {'id': user_id})

    def delete_sub_user(self, user_id):
        """Delete a sub-user."""
        return self._call('subDeleteSubUser', {'id': user_id})

    def modify_sub_user_status(self, user_id, status):
        """Modify sub-user status."""
        return self._call('subModifyStatus', {'id': user_id, 'status': status})

    def modify_sub_user_password(self, user_id, password):
        """Modify sub-user password."""
        return self._call('subModifyPassword', {'id': user_id, 'password': password})

    def delegate_zone_to_sub_user(self, user_id, zone):
        """Delegate zone to sub-user."""
        return self._call('subDelegateZone', {'id': user_id, 'zone': zone})

    def remove_zone_delegation(self, user_id, zone):
        """Remove zone delegation from sub-user."""
        return self._call('subRemoveZoneDelegation', {'id': user_id, 'zone': zone})

    # =========================================================================
    # Helper Methods for Record Management
    # =========================================================================

    def ensure_record(
        self,
        domain_name,
        host,
        record_type,
        value,
        ttl,
        state='present',
        **kwargs
    ):
        """
        Ensure a DNS record exists or is absent (idempotent).

        This is the main method used by Ansible modules for idempotent
        record management.

        Args:
            domain_name: The domain name
            host: Host name
            record_type: Record type (A, AAAA, CNAME, etc.)
            value: Record value (required for state=present)
            ttl: TTL value
            state: 'present' or 'absent'
            **kwargs: Additional record parameters

        Returns:
            dict: Result with 'changed', 'msg', and optional 'data' keys
        """
        result = {
            'changed': False,
            'msg': '',
            'data': None,
        }

        try:
            # Get existing records
            existing = self.list_records(domain_name, host=host, record_type=record_type)

            if state == 'present':
                if not value:
                    raise ClouDNSError("Value is required when state is 'present'")

                # Check if record already exists
                matching_record = None
                for record_id, record in existing.items():
                    if record.get('record') == value:
                        matching_record = (record_id, record)
                        break

                if matching_record:
                    record_id, record = matching_record
                    # Check if TTL needs updating
                    current_ttl = int(record.get('ttl', 0))
                    if current_ttl != int(ttl):
                        # Update the record
                        api_response = self.modify_record(
                            domain_name=domain_name,
                            record_id=record_id,
                            host=host,
                            value=value,
                            ttl=ttl,
                            **kwargs
                        )
                        result['changed'] = True
                        result['msg'] = f"Record updated (TTL changed from {current_ttl} to {ttl})"
                        result['data'] = api_response
                    else:
                        result['msg'] = "Record already exists with correct value and TTL"
                else:
                    # No matching record, check if we should update or create
                    if len(existing) == 1:
                        # One record exists but value differs - update it
                        record_id = list(existing.keys())[0]
                        api_response = self.modify_record(
                            domain_name=domain_name,
                            record_id=record_id,
                            host=host,
                            value=value,
                            ttl=ttl,
                            **kwargs
                        )
                        result['changed'] = True
                        result['msg'] = "Record updated with new value"
                        result['data'] = api_response
                    elif len(existing) == 0:
                        # No records exist - create new
                        api_response = self.add_record(
                            domain_name=domain_name,
                            record_type=record_type,
                            host=host,
                            value=value,
                            ttl=ttl,
                            **kwargs
                        )
                        result['changed'] = True
                        result['msg'] = "Record created"
                        result['data'] = api_response
                    else:
                        # Multiple records exist - ambiguous
                        raise ClouDNSError(
                            f"Multiple records found for {host}.{domain_name} ({record_type}). "
                            "Cannot determine which to update. Please delete extras first."
                        )

            elif state == 'absent':
                if not existing:
                    result['msg'] = "Record does not exist"
                else:
                    deleted_count = 0
                    for record_id, record in existing.items():
                        # If value specified, only delete matching records
                        if value and record.get('record') != value:
                            continue
                        self.delete_record(domain_name, record_id)
                        deleted_count += 1

                    if deleted_count > 0:
                        result['changed'] = True
                        result['msg'] = f"Deleted {deleted_count} record(s)"
                    else:
                        result['msg'] = "No matching records to delete"

            else:
                raise ClouDNSError(f"Invalid state: {state}")

        except ClouDNSError as e:
            result['failed'] = True
            result['msg'] = str(e)

        return result


# Convenience function for creating clients
def create_client(auth_id, auth_password, is_subuser=False, **kwargs):
    """
    Factory function to create a ClouDNS client.

    Args:
        auth_id: API auth ID or sub-user ID
        auth_password: API password
        is_subuser: True for sub-user authentication
        **kwargs: Additional client options

    Returns:
        ClouDNSClient: Configured client instance
    """
    return ClouDNSClient(
        auth_id=auth_id,
        auth_password=auth_password,
        is_subuser=is_subuser,
        **kwargs
    )
