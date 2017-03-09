# SnapServ Monitoring Plugins

[![License](http://img.shields.io/badge/license-GPL--3.0+-blue.svg)](https://github.com/SnapServ/monitoring-plugins/LICENSE.txt)
[![Python Compatibility](http://img.shields.io/badge/python_compatibility-3.3_--_3.6-brightgreen.svg)](#)
[![GitHub issues](https://img.shields.io/github/issues/SnapServ/monitoring-plugins.svg)](https://github.com/SnapServ/monitoring-plugins/issues)
[![Python Compatibility](http://img.shields.io/badge/copyright-SnapServ_Mathis-lightgrey.svg)](#)

### Table of Contents

- [Introduction](#introduction)
- [Overview](#overview)
- [Changelog](#changelog)
- [Copyright](#copyright)

## Introduction

*SnapServ/monitoring-plugins* is a repository containing miscellaneous Nagios /
Icinga plugins. Project goals include:

- No unnecessary dependencies - keep it simple, stupid
- Compatibility with Python v3.3 - v3.6
- Clean code with sane error checking
- Usage of *nagiosplugin* library, to keep everything pretty and consistent

We recommend to automatically deploy this repository to a specific path by using
Ansible/Salt/Puppet/Chef, so that the plugins can be easily updated.
Additionally, we recommend to setup a virtualenv within that folder, so that
dependencies are isolated from the Python system installation.

The folder *commands/* contains working Icinga2 check command definitions which
can be used as-is in most situations. You can easily create a symlink to that
folder within your Icinga2 configuration folder.

## Overview

As of today, the following monitoring plugins exist:

- **check_bird_bgp**: Connects to the BIRD/BIRD6 routing daemon control socket
  and gathers information about a BGP protocol with a specified name. The
  service will result in WARNING or CRITICAL (user-configurable severity) if the
  session goes down or any other errors occur. Additionally, this plugin can
  monitor the protocol for filtered routes or if the usage of the configured
  receive limit, if any, is between an expected range.

- **check_linux_dns**: Checks the domain name resolution with a specific server
  or if not provided, the system DNS resolvers. Query name and type can
  specified and the script will also monitor the response time, so that alerts
  can be triggered when a DNS server replies slow or not at all.

- **check_linux_interface**: Checks if an interface with a given name exists and
  is 'UP'. Returns CRITICAL as service state in all other situations.

- **check_linux_load**: Checks the current system load and reports the average
  1min/5min/15min load as performance data. Data can also be shown with a
  *per-cpu* option, which will divide the result by the amount of CPU cores.

- **check_linux_memory**: Checks the current memory usage and alerts if a given
  threshold is exceeded. The user can choose if cache data should be either
  counted as used or free memory.

- **check_linux_uptime**: Checks the current system uptime and alerts if the
  uptime is outside of an expected range. This can be used to detect unplanned
  system reboots / crashes.

- **check_xmpp**: Checks a XMPP server by testing the whole connection setup
  according to the official XMPP protocol specifications. Also supports StartTLS
  and certificate expiry checks, if desired.

## Changelog
```
1.0.0 (2017-03-09)
    Initial release of ssmp (SnapServ Monitoring Plugins)
```

## Copyright

Copyright &copy; 2016 - 2017 SnapServ Mathis. All rights reserved.
