# ☁️ Virtualization Patch Guidelines

> **Domain**: Infrastructure / Virtualization
> **Scope**: VMware, Citrix, Cloud Management

This directory contains the job instructions for AI Agents to perform quarterly patch analysis for virtualization platforms and cloud management tools.

## 📋 Target Products Scope

The following virtualization products are within the scope of the Patch Review Board:

### VMware by Broadcom
- **Compute Virtualization**:
    - vSphere ESXi
    - vSphere Replication
- **Management**:
    - vSphere vCenter Server
    - Aria (formerly vRealize Suite)
- **Storage & Networking**:
    - vSAN (Virtual SAN)
    - NSX (Network Virtualization)
- **BC/DR**:
    - VMware Live Site Recovery (formerly Site Recovery Manager / SRM)

### Citrix
- **Citrix Hypervisor** (formerly XenServer)
- **XenCenter** (Management Console)

---

## 📄 Available Instructions

| File | Description | Target Agent |
| :--- | :--- | :--- |
| *TBD* | *Instructions for Hypervisor patching are under development.* | - |

---

## 🔍 Patch Selection Strategy (General)

While specific instructions are being developed, the general selection criteria for virtualization prioritize:
1.  **Host Stability**: Fixes for PSOD (Purple Screen of Death) or host lockups.
2.  **Guest Isolation**: Fixes for CVEs allowing VM escape or side-channel attacks.
3.  **Storage Access**: Fixes for APD (All Paths Down) or PDL (Permanent Device Loss) scenarios.
4.  **Management Plane**: Fixes for vCenter downtime or database corruption.
