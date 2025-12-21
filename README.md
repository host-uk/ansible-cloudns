# ClouDNS Ansible Collection

This repository contains the ClouDNS Ansible Collection, which allows you to manage ClouDNS resources (specifically DNS records) using Ansible.

It leverages the [official ClouDNS PHP SDK](https://github.com/ClouDNS/cloudns-php-sdk) to communicate with the API.

## Requirements

- PHP 5.0 or higher must be installed on the machine where the module runs (usually the target node, or localhost if using `connection: local`).
- Ansible 2.9+

## Installation

You can install this collection directly from the repository or by building it.

### From Source

```bash
ansible-galaxy collection install git+https://github.com/ClouDNS/cloudns-php-sdk.git
```

## Usage

### Modules

* `cloudns.cloudns.record`: Manage DNS records.

### Example Playbook

```yaml
- hosts: localhost
  connection: local
  tasks:
    - name: Ensure A record exists
      cloudns.cloudns.record:
        auth_id: 1234
        auth_password: "your_password"
        domain: example.com
        host: www
        type: A
        value: 1.2.3.4
        state: present

    - name: Update IP for a server
      cloudns.cloudns.record:
        auth_id: 1234
        auth_password: "your_password"
        domain: example.com
        host: server1
        type: A
        value: 10.0.0.1
```

## SDK Information

The PHP SDK code is located in `plugins/module_utils/php/` and is used internally by the module.

## License

This collection includes the ClouDNS SDK which is licensed under its own terms.
