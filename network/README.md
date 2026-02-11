# 🌐 Network Equipment Patch Guidelines

> **Domain**: Infrastructure / Networking
> **Scope**: Cisco, F5, Fortinet, Secui

This directory contains the job instructions for AI Agents to perform quarterly patch analysis for network infrastructure.

## 📋 Target Products Scope

The following network devices and platforms are within the scope of the Patch Review Board:

### Cisco Systems
- **Catalyst Series** (Access/Core Switching):
    - Catalyst 2960, 3650, 3850
    - Catalyst 6500 (Legacy Core)
    - Catalyst 9200, 9300, 9400, 9600 (Modern Intent-Based Networking)
- **Nexus Series** (Data Center Switching):
    - Nexus 3K, 5K, 7K, 9K
    - Cisco NDFC (Nexus Dashboard Fabric Controller)
- **Routing**:
    - ASR (Aggregation Services Routers)
    - ISR (Integrated Services Routers)

### Load balancers & ADC
- **F5 Networks**: BIG-IP LTM (Local Traffic Manager)
- **A10 Networks**: Thunder Series (TH)

### Security / Firewalls
- **Fortinet**: Fortigate Next-Generation Firewalls
- **Secui**:
    - BLUEMAX (NGFW)
    - MF2 (Multifunction Firewall)

---

## 📄 Available Instructions

| File | Description | Target Agent |
| :--- | :--- | :--- |
| *TBD* | *Instructions for Network OS (IOS-XE, NX-OS, TMOS, FortiOS) are under development.* | - |

---

## 🔍 Patch Selection Strategy (General)

While specific instructions are being developed, the general selection criteria for network devices prioritize:
1.  **Exploitable Vulnerabilities**: Fixes for known CVEs accessible via management interfaces or data plane.
2.  **Protocol Stability**: Fixes for routing protocol (BGP, OSPF) crashes or memory leaks.
3.  **Forwarding Plane**: Fixes for packet drops, ASIC programming errors, or throughput degradation.
4.  **Management Plane**: Fixes for SSH/HTTPS access, SNMP monitoring, and automation API stability.
