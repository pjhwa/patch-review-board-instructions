# 🐧 Operating System (Linux) Patch Guidelines

> **Domain**: Infrastructure / Operating Systems
> **Scope**: Red Hat Enterprise Linux, Ubuntu LTS, Oracle Linux

This directory contains the specific job instructions for AI Agents to perform quarterly patch analysis for Linux-based operating systems.

## 📄 Available Instructions

| File | Description | Target Agent |
| :--- | :--- | :--- |
| [`PRB_Instruction-Linux.md`](PRB_Instruction-Linux.md) | Comprehensive guide for RHEL, Ubuntu, and Oracle Linux patch recommendation. | OpenClaw / AI Agent |

---

## 🔍 Deep Dive: Linux Patch Selection Strategy

The instructions in this directory implement a rigorous **Stability-First** approach to patch management. Unlike simple "apply all updates" strategies, this protocol focuses on identifying high-impact fixes that prevent service outages.

### 1. Tri-OS Coverage Model
The guidelines unify the research process across three major enterprise Linux distributions, accounting for their specific advisory formats:
- **Red Hat (RHEL)**: Focuses on **Red Hat Security Advisories (RHSA)** and **Bug Fix Advisories (RHBA)** with "Critical" or "Important" severity.
- **Ubuntu LTS**: Targets **Ubuntu Security Notices (USN)**, correlating them with upstream CVEs.
- **Oracle Linux**: Analyzes **Oracle Linux Security Advisories (ELSA)**, specifically tracking Unbreakable Enterprise Kernel (UEK) updates.

### 2. Full-Stack Scope (Beyond the Kernel)
A critical innovation in these instructions is the expansion of scope beyond the kernel. Modern infrastructure issues often originate in the "user space" core.
- **System Stability**: `systemd`, `udev` (Boot & Service Management)
- **Data Path**: `multipath-tools`, `lvm2` (Storage Integrity)
- **Networking**: `NetworkManager`, `firewalld` (Connectivity)
- **Security**: `openssl`, `glibc` (Core Libraries)

### 3. "The 7 Pillars" Selection Criteria
The AI Agent is trained to filter thousands of patches down to a vital few based on these seven pillars:
1.  **Widespread Impact**: Is this bug affecting many global users?
2.  **Hang/Crash Fixes**: Does this patch prevent a kernel panic or service crash?
3.  **Data Safety**: Does it fix potential data corruption or loss scenarios?
4.  **Hardware Ops**: Does it resolve driver/firmware conflicts?
5.  **Failover Safety**: Does it ensure HA mechanisms (e.g., Pacemaker) work correctly?
6.  **Critical Security**: Does it close a CVSS 9.0+ vulnerability?
7.  **Service Continuity**: Does it prevent massive service interruptions?

---

## 🛠️ Execution Workflow for Agents

1.  **Context Loading**: Agent loads `PRB_Instruction-Linux.md`.
2.  **Timeframe Definition**: Agent identifies the target quarter (e.g., Nov-Jan).
3.  **Parallel Research**: Agent queries vendor portals (Red Hat Access, Canonical, Oracle Linux Security) concurrently.
4.  **Filtering & deduplication**:
    - Selects the *latest* version if multiple updates exist for a package.
    - Aggregates descriptions to include all intermediate fixes.
5.  **Localization**: Translates technical descriptions into professional Korean summaries.
6.  **Report Generation**: Outputs a CSV ready for the Patch Review Board's decision.

---

*For updates or contributions to these guidelines, please submit a Pull Request to the `master` branch.*
