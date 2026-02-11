# 💾 Storage Patch Guidelines

> **Domain**: Infrastructure / Storage
> **Scope**: Dell EMC, Hitachi Vantara, HPE, NetApp

This directory contains the job instructions for AI Agents to perform quarterly patch analysis for enterprise storage systems.

## 📋 Target Products Scope

The following storage arrays and platforms are within the scope of the Patch Review Board:

### Dell EMC
- **Block & Unified**:
    - PowerStore, PowerMAX, VMAX, VNX, Unity, XtremIO
    - SC Series (Compellent), EqualLogic (PS Series), PowerVault
- **File & Object**: Isilon, ECS (Elastic Cloud Storage)
- **Networking**: Connectrix (Brocade, Cisco MDS)

### Hitachi Vantara (HPE Alletra 9000 included)
- **VSP Series**:
    - VSP 5000, G Series, F Series, E Series
    - VSP One Block, VSP One File
- **Midrange / Legacy**:
    - HUS (Hitachi Unified Storage), HUS VM
    - AMS (Adaptable Modular Storage)
    - HNAS (Hitachi NAS Platform)
    - USP (Universal Storage Platform)
- **Others**: Brocade SAN Switches (OEM)

### HPE (Hewlett Packard Enterprise)
- **Primary Storage**: Alletra, Primera, 3PAR StoreServ

### NetApp
- **Unified Storage**: AFF (All Flash FAS), FAS (Fabric Attached Storage)

---

## 📄 Available Instructions

| File | Description | Target Agent |
| :--- | :--- | :--- |
| *TBD* | *Instructions for Storage OS (PowerScale OneFS, ONTAP, SVOS) are under development.* | - |

---

## 🔍 Patch Selection Strategy (General)

While specific instructions are being developed, the general selection criteria for storage systems prioritize:
1.  **Data Durability**: Fixes for RAID calculation errors, SSD firmware bugs, or filesystem corruption.
2.  **Controller Resilience**: Fixes for dual-controller failover logic, cache coherence issues, and memory leaks.
3.  **Connectivity**: Fixes for Fibre Channel / iSCSI host path flakiness or protocol errors.
4.  **Replication**: Fixes for async/sync replication lag or data inconsistency between sites.
