# SnapServ Monitoring Plugins

[![License](http://img.shields.io/badge/license-GPL--3.0+-blue.svg)](https://github.com/SnapServ/monitoring-plugins/LICENSE.txt)
[![Python Compatibility](http://img.shields.io/badge/python_compatiblity-2.7_and_3.3--3.5-brightgreen.svg)](#)
[![GitHub issues](https://img.shields.io/github/issues/badges/shields.svg)](https://github.com/SnapServ/monitoring-plugins/issues)
[![Python Compatibility](http://img.shields.io/badge/copyright-SnapServ_--_Pascal_Mathis-lightgrey.svg)](#)

### Table of Contents

- [Introduction](#introduction)
- [Overview](#overview)
- [Icinga2 Check Commands](#icinga2-check-commands)
    - [check_linux_dns](#check_linux_dns)
    - [check_linux_memory](#check_linux_memory)
    - [check_linux_uptime](#check_linux_uptime)
    - [check_mikrotik_bgp_peer](#check_mikrotik_bgp_peer)
    - [check_xmpp](#check_xmpp)
- [Copyright](#copyright)

## Introduction

*SnapServ/monitoring-plugins* is a repository containing miscellaneous Nagios /
Icinga plugins. Project goals include:

- No unnecessary dependencies - keep it simple, stupid
- Compatibility with Python v2.7 and v3.3 - v3.5
- Clean code with sane error checking
- Usage of *nagiosplugin* library, to keep everything pretty and consistent

## Overview

As of today, the following monitoring plugins exist:

- **check_linux_dns**: Checks the domain name resolution with a specific server
  or if not provided, the system DNS resolvers. Query name and type can
  specified and the script will also monitor the response time, so that alerts
  can be triggered when a DNS replies slow or not at all.

- **check_linux_load**: Checks the current system load and reports the average
  1min/5min/15min load as performance data. Data can also be shown with a
  *per-cpu* option, which will divide the result by the amount of CPU cores.

- **check_linux_memory**: Checks the current memory usage and alerts if a given
  threshold is exceeded. The user can choose if cache data should be either
  counted as used or free memory.

- **check_mikrotik_bgp_peer**: Connects to a Mikrotik RouterOS device and
  collects information about a BGP peer with a specific name. Various
  performance data (received/transmitted updates, withdrawals) will be provided.
  If desired, the user can also monitor the current usage of the
  *max-prefix-limit* in percent and alert when it exceeds a given range.

- **check_xmpp**: Checks a XMPP server by testing the whole connection setup.
  Also supports StartTLS and certificate expiry checks, if desired.

## Icinga2 Check Commands

### check_linux_dns

```
object CheckCommand "linux_memory" {
	import "plugin-check-command"

	command = [ PluginDir + "/ssx/check_linux_memory" ]

	arguments = {
		"-c" = "$memory_free_percentage_critical_range$",
		"-w" = "$memory_free_percentage_warning_range$",
		"-f" = {
			set_if = "$memory_cached_as_free$"
			description = "Count cached memory as free."
		}
	}
}
```

### check_linux_memory

```
object CheckCommand "linux_memory" {
	import "plugin-check-command"

	command = [ PluginDir + "/ssx/check_linux_memory" ]

	arguments = {
		"-c" = "$memory_free_percentage_critical_range$",
		"-w" = "$memory_free_percentage_warning_range$",
		"-f" = {
			set_if = "$memory_cached_as_free$"
			description = "Count cached memory as free."
		}
	}
}
```

### check_linux_uptime

```
object CheckCommand "linux_uptime" {
	import "plugin-check-command"

	command = [ PluginDir + "/ssx/check_linux_uptime" ]

	arguments = {
		"-c" = "$uptime_critical_range$",
		"-w" = "$uptime_warning_range$",
	}
}
```

### check_mikrotik_bgp_peer

```
object CheckCommand "mikrotik_bgp_peer" {
	import "plugin-check-command"

	command = [ PluginDir + "/ssx/check_mikrotik_bgp_peer" ]

	arguments = {
		"--host" = "$api_host$"
		"--username" = "$api_username$"
		"--password" = "$api_password$"
		"-p" = "$bgp_peer_name$"
		"-l" = "$bgp_peer_maxpref_range$"
		"-c" = {
			set_if = "$bgp_peer_critical$"
			description = "Mark the BGP peering session as critical."
		}
	}

	vars.api_host = "$address$"
}
```

### check_xmpp

```
object CheckCommand "xmpp" {	import "plugin-check-command"

	command = [ PluginDir + "/ssx/check_xmpp" ]

	arguments = {
		"-s" = "$xmpp_server$"
		"-p" = "$xmpp_port$"
		"-H" = "$xmpp_host$"
		"-w" = "$xmpp_warning_rt$"
		"-c" = "$xmpp_critical_rt$"
		"--warning-days" = "$xmpp_warning_days$"
		"--critical-days" = "$xmpp_critical_days$"
		"--starttls" = {
			set_if = "$xmpp_force_starttls$"
			description = "Enforce usage of StartTLS."
		}
		"--no-check-certificates" = {
			set_if = "$xmpp_disable_certificate_checks$"
			description = "Disable all certificate checks."
		}
		"--ca-roots" = "$xmpp_ca_roots$"
		"--c2s" = {
			set_if = "$xmpp_use_c2s$"
			description = "Use C2S mode when checking the XMPP server. (default)"
		}
		"--s2s" = {
			set_if = "$xmpp_use_s2s$"
			description = "Use S2S mode when checking the XMPP server."
		}
		"-4" = {
			set_if = "$xmpp_force_ipv4$"
			description = "Force the XMPP check to use IPv4."
		}
		"-6" = {
			set_if = "$xmpp_force_ipv6$"
			description = "Force the XMPP check to use IPv6."
		}
	}

	vars.xmpp_server = "$host_name$"
}
```

## Copyright

Copyright &copy; 2016 SnapServ - Pascal Mathis. All rights reserved.
