# 🛡️ Patch Review Board (PRB) Job Instructions

> **Operational Guidelines for AI Agents in Infrastructure Stability Assurance**

This repository hosts the canonical job instructions for **AI Agents** serving as members of the **Patch Review Board (PRB)**. These instructions define the logic, criteria, and processes for selecting and recommending critical updates to ensure the stability and security of enterprise infrastructure.

---

## 📂 Repository Structure

The instructions are organized by infrastructure domain to facilitate modular expansion and specialized agent assignments.

```plaintext
patch-review-board-instructions/
├── 🐧 os/                # Operating System (Linux) patch guidelines
│   └── PRB_Instruction-Linux.md
├── 🗄️ database/          # Database patch guidelines (Placeholder)
├── 🌐 network/           # Network equipment patch guidelines (Placeholder)
├── 💾 storage/           # Storage system patch guidelines (Placeholder)
├── ☁️ virtualization/    # Virtualization platform guidelines (Placeholder)
└── 🔗 middleware/        # Middleware patch guidelines (Placeholder)
```

---

## 🤖 Operating Model

### Role & Objective
- **Role**: Infrastructure Operations Stability AI Agent
- **Objective**: Proactively identify specific, critical patches to prevent service disruptions in On-Premise and Cloud environments.
- **Cadence**: Quarterly (End of Mar, Jun, Sep, Dec)
- **Scope**: Patches released within the last **3 months**.

### Targeted Platforms (OS)
| Platform | Versions |
| :--- | :--- |
| **Red Hat Enterprise Linux** | 8, 9, 10 |
| **Ubuntu LTS** | 22.04, 24.04 |
| **Oracle Linux** | 8, 9, 10 |

---

## 🎯 Selection Criteria & Scope

The AI Agent evaluates patches based on the following strict criteria to filter noise and focus on impact.

### ✅ Selection Criteria (Must-Have)
Patches are selected if they address one or more of the following:
1.  **System Stability** 🛑: Fixes for system/application Hangs or Crashes.
2.  **Data Integrity** 💾: Fixes for Data Loss (DL) or Data Unavailability (DU).
3.  **Security** 🔒: Mitigation of **Critical** or **High Severity** vulnerabilities (CVEs).
4.  **Hardware Control** ⚙️: Fixes for controller or hardware malfunctions.
5.  **Failover Assurance** 🔄: Fixes preventing HA (High Availability) failover.
6.  **Widespread Impact** 🌍: Bugs affecting a large percentage of deployments.

### 📦 Target Package Scope
Verification is **not limited to the Kernel**. The full stack is considered:
- **Foundations**: Kernel, Firmware, Device Drivers (Storage, Network, GPU)
- **Core Services**: systemd, udev, journald, dbus
- **Network Stack**: NetworkManager, firewalld, iptables, iproute
- **Filesystem**: lvm2, xfsprogs, multipath-tools, nfs-utils
- **Security & Libs**: glibc, openssl, selinux-policy, sudo

---

## 🚀 Usage

These instructions are designed to be ingested by LLM-powered agents (e.g., via RAG or context loading).

**Example Prompt for AI Agent:**
> "Act as the Infrastructure Stability AI Agent. Read the `os/PRB_Instruction-Linux.md` file. Perform the quarterly patch research for the period [Start Date] to [End Date] following the criteria and output the results in the specified CSV format."

---

## 📝 Output Format

Results are generated in a standardized CSV format for automated processing and human review:
- **Columns**: `Category`, `Release Date`, `Vendor`, `Model/Version`, `Detailed Version`, `Patch Name`, `Patch Target`, `Reference Site`, `Patch Description` (EN), `Korean Description` (KR).
- **Localization**: Includes concise, professional Korean summaries (noun-ending style) for rapid decision-making by Korean operators.

---
*Maintained by Infrastructure Operation Team*
