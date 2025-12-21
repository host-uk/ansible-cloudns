# ClouDNS Ansible Collection

This repository contains the ClouDNS Ansible Collection (`host_uk.cloudns`), which allows you to manage ClouDNS resources (specifically DNS records) using Ansible.

It leverages the [official ClouDNS PHP SDK](https://github.com/ClouDNS/cloudns-php-sdk) to communicate with the API.

## Requirements

You can run the PHP code using either a local PHP installation OR via Docker.

### Option 1: Local PHP
- PHP 5.0 or higher must be installed on the machine where the module runs (usually the target node, or localhost if using `connection: local`).
- `php-curl` and `php-json` extensions should be enabled.

### Option 2: Docker
- Docker must be installed and running on the machine where the module runs.
- The module will use a PHP image (default `php:cli`) to execute the SDK.

- Ansible 2.9+

## Installation

You can install this collection directly from the repository.

```bash
ansible-galaxy collection install git+https://github.com/ClouDNS/cloudns-php-sdk.git
```

## Usage

### Modules

* `host_uk.cloudns.record`: Manage DNS records.

### Example Playbook

#### Using Local PHP

```yaml
- hosts: localhost
  connection: local
  tasks:
    - name: Ensure A record exists
      host_uk.cloudns.record:
        auth_id: 1234
        auth_password: "your_password"
        domain: example.com
        host: www
        type: A
        value: 1.2.3.4
        state: present
```

#### Using Docker

If you don't want to install PHP on the target machine, you can use Docker:

```yaml
- hosts: localhost
  connection: local
  tasks:
    - name: Update IP for a server using Docker
      host_uk.cloudns.record:
        auth_id: 1234
        auth_password: "your_password"
        domain: example.com
        host: server1
        type: A
        value: 10.0.0.1
        use_docker: true
        docker_image: php:8.2-cli
```

## SDK Information

The PHP SDK code is located in `plugins/module_utils/php/` and is used internally by the module.

## License

This collection includes the ClouDNS SDK which is licensed under its own terms.
