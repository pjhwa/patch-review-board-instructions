# 🛡️ Patch Review Board (PRB) Job Instructions

> **Operational Guidelines for AI Agents in Infrastructure Stability Assurance**

This repository hosts the canonical job instructions for **AI Agents** serving as members of the **Patch Review Board (PRB)**. These instructions define the logic, criteria, and processes for selecting and recommending critical updates to ensure the stability and security of enterprise infrastructure.

---

## 📂 Repository Structure & Target Products

The instructions are organized by infrastructure domain. Each directory contains detailed guidelines for the specific technology stack.

### 🐧 [os/](os/README.md) (Operating Systems)
> **Representative Products**: RHEL, Ubuntu, Windows Server, Oracle Linux, Unix (AIX, HP-UX, Solaris)
- Detailed Analysis: [`os/README.md`](os/README.md)
- Instructions: [`PRB_Instruction-Linux.md`](os/PRB_Instruction-Linux.md)

### 🗄️ [database/](database/README.md) (Databases)
> **Representative Products**: Oracle Database, Microsoft SQL Server, MySQL, PostgreSQL
- Detailed Analysis: [`database/README.md`](database/README.md)

### 🌐 [network/](network/README.md) (Network)
> **Representative Products**: Cisco (Catalyst, Nexus, ASR), F5 BIG-IP, Fortinet Fortigate
- Detailed Analysis: [`network/README.md`](network/README.md)

### 💾 [storage/](storage/README.md) (Storage)
> **Representative Products**: Dell EMC (PowerStore, VMAX), Hitachi VSP, NetApp AFF/FAS
- Detailed Analysis: [`storage/README.md`](storage/README.md)

### 🔗 [middleware/](middleware/README.md) (Middleware)
> **Representative Products**: Apache Tomcat, Oracle WebLogic, JBoss EAP, Nginx
- Detailed Analysis: [`middleware/README.md`](middleware/README.md)

### ☁️ [virtualization/](virtualization/README.md) (Virtualization)
> **Representative Products**: VMware vSphere, Citrix Hypervisor, VMware NSX
- Detailed Analysis: [`virtualization/README.md`](virtualization/README.md)

---

## 🤖 Operating Model

### Role & Objective
- **Role**: Infrastructure Operations Stability AI Agent
- **Objective**: Proactively identify specific, critical patches to prevent service disruptions in On-Premise and Cloud environments.
- **Cadence**: Quarterly (End of Mar, Jun, Sep, Dec)
- **Scope**: Patches released within the last **3 months**.

---

## 🎯 Selection Criteria (Global Standard)

The AI Agent evaluates patches based on the following strict criteria to filter noise and focus on impact.

### ✅ Selection Criteria (Must-Have)
Patches are selected if they address one or more of the following:
1.  **System Stability** 🛑: Fixes for system/application Hangs or Crashes.
2.  **Data Integrity** 💾: Fixes for Data Loss (DL) or Data Unavailability (DU).
3.  **Security** 🔒: Mitigation of **Critical** or **High Severity** vulnerabilities (CVEs).
4.  **Hardware Control** ⚙️: Fixes for controller or hardware malfunctions.
5.  **Failover Assurance** 🔄: Fixes preventing HA (High Availability) failover.
6.  **Widespread Impact** 🌍: Bugs affecting a large percentage of deployments.

---
*Maintained by Infrastructure Operation Team*
