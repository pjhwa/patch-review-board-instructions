---
name: Patch Review Board (PRB) Operation
description: Instructions for AI Agents to perform the quarterly OS Patch Review process for Red Hat, Oracle Linux, and Ubuntu.
---

# Patch Review Board (PRB) Operation

This skill guides the AI Agent through the end-to-end process of generating a validated OS Patch Recommendation Report. The process involves collecting patch data, filtering out non-critical components, performing a deep impact analysis (LLM Check), and generating a final CSV report.

## 1. Prerequisites & Setup

Ensure the following scripts are available in your workspace (or download them from the internal repository `github.com/my-org/patch-review-automation`):

- `batch_collector.js` (Data Collection)
- `patch_preprocessing.py` (Pruning & Aggregation)

## 2. Process Workflow

### Step 1: Data Collection & Ingestion
Execute the collection scripts to gather the latest advisory data from vendor sources (RSS/Web).

```bash
# Example: Collect data for the current quarter
node batch_collector.js --quarter "2026-Q1"
```
*Goal: Ensure `patch_review_summary.md` and `extracted_data/` are populated.*

### Step 2: Pruning & Aggregation (Automated)
Run the preprocessing script to filter out non-critical components (e.g., applications like `python-urllib3`) and aggregate multiple patches for the same component.

```bash
python patch_preprocessing.py
```
*Goal: Generate `patches_for_llm_review.json`. This file contains the filtered, consolidated list of candidates.*

### Step 3: Impact Analysis (Actual Agent Review)
**Action Required:** Read the `patches_for_llm_review.json` file. The Agent must **manually analyze** each candidate's `full_text` and `history` to determine if it meets the **Critical System Impact** criteria. **Do not rely on simple scripts for this step.**

**Cumulative Recommendation Logic (CRITICAL):**
If a component has multiple updates within the quarter (e.g., kernel-5, kernel-4, kernel-3, kernel-2, kernel-1):
1.  **Identify Critical Versions:** Determine which versions in the history contain *Critical* fixes (e.g., kernel-3 and kernel-1 are Critical; kernel-5, kernel-4, kernel-2 are Not Critical).
2.  **Recommend Latest CRITICAL Version:** Select the **latest version that is Critical** (e.g., **kernel-3**). cannot simply recommend the absolute latest (kernel-5) if it is just a minor/non-critical update.
3.  **Aggregate Critical Descriptions:** In the **Description**, merge only the critical fix details from the selected version (kernel-3) and any older critical versions (kernel-1). Do not include noise from non-critical versions.

**Criteria for Inclusion:**
- **System Hang/Crash**: Kernel panics, deadlocks, boot failures.
- **Data Loss/Corruption**: Filesystem errors, raid failures, data integrity issues.
- **Critical Performance**: Severe degradation affecting service capability.
- **Security (Critical)**: RCE (Remote Code Execution), Privilege Escalation (Root), Auth Bypass.
- **Failover Failure**: Issues affecting High Availability (Pacemaker, Corosync).

**Criteria for Exclusion:**
- Minor bug fixes (typos, logging noise).
- Edge cases not affecting stability.
- "Moderate" security issues (local DoS, info leak) unless widespread.
- **Support Window Exclusion (Ubuntu)**:
    - **Do NOT** include patches affecting *only* non-LTS versions (e.g., Ubuntu 25.10, 24.10).
    - **MUST** prioritize LTS versions (24.04, 22.04, 20.04).
    - *Example:* "USN-7906-1 affects only Ubuntu 25.10 -> **EXCLUDE**."
- **Specific Version Lookup**:
    - For Red Hat patches, the `full_text` often lacks the specific RPM version.
    - **Action**: If `specific_version` is missing in `patches_for_llm_review.json`:
        1. Search the Red Hat Customer Portal for the Advisory ID (e.g., `RHSA-2026:1815`).
        2. Go to the "Updated Packages" tab.
        3. Identify the primary RPM version (e.g., `openssh-8.7p1-30.el9_2.9`).
        4. Add an entry to the `extract_specific_version` function in `patch_preprocessing.py`.
        5. Re-run `python patch_preprocessing.py`.

### Step 4: Final Report Generation
Generate the `patch_review_final_report.csv` file.

**Format:**
```csv
Issue ID,Vendor,Dist Version,Component,Version,Date,Criticality,Patch Description,한글 설명,Reference
```

**Content Guidelines (CRITICAL):**
- **Dist Version**:
    - **MUST** be populated with the specific OS version from the JSON `dist_version` field.
    - Ubuntu: e.g., `"22.04 LTS"`, `"24.04 LTS"`. Oracle: e.g., `"9"`, `"8"`. RHEL: e.g., `"9"`, `"8"`.
    - If a patch covers **multiple versions**, create **one row per version** in the CSV.
    - *Example:* USN-7851-2 → two rows: one for `22.04 LTS`, one for `24.04 LTS`.
- **Reference**:
    - **MUST** be populated with the `ref_url` (or `url`) field from the source JSON.
    - **Do NOT** leave as "Unknown" if a URL is available in the source data.
- **Version**:
    - **MUST** be the specific package version for that particular `Dist Version`.
    - If `USN` or `RHSA` refers to multiple packages, ensure you pick the one matching the `Dist Version`.
- **한글 설명 (Korean Description)**:
    - **Do NOT** use generic phrases like "Security update for kernel" or simply list CVE IDs.
    - **MUST** detailed specific critical bugs. Explain **what** functionality is broken and **how** it affects the system.
    - **Keywords to look for**: "System Hang", "Memory Leak", "Race Condition", "Use-After-Free", "Data Corruption", "Panic".
    - *Example (Bad):* "커널 보안 업데이트 및 버그 수정."
    - *Example (Good):* "메모리 부족 상황에서 데이터 손실을 유발할 수 있는 zswap 경쟁 상태 해결 및 `nilfs_mdt_destroy`의 일반 보호 오류(GPF)로 인한 시스템 크래시 방지."

- **Patch Description (English)**:
    - **Do NOT** simply copy/paste the `diff_summary` or log.
    - **MUST** be a **synthesized summary** of the **Korean Description**.
    - It should convey the exact same critical impact and specific fix details as the Korean text, but in English.
    - *Example:* "Resolves Race Condition in zswap causing potential data loss under memory pressure. Fixes General Protection Fault (GPF) in `nilfs_mdt_destroy` preventing system crashes."

**Note:** Ensure the description reflects that it is a cumulative update if applicable.

## 3. Execution Example

**User Request:** "Run the PRB for Q1 2026."

**Agent Actions:**
1.  Run `node batch_collector.js ...`
2.  Run `python patch_preprocessing.py`
3.  Read `patches_for_llm_review.json`.
4.  *Thinking Process*:
    *   "Candidate: kernel-uek... Impacts: Data Loss. -> **INCLUDE**."
    *   "Candidate: python-libs... Impacts: Minor fix. -> **EXCLUDE**."
5.  Create `patch_review_final_report.csv` with the approved list.
6.  Notify User: "Report generated at [path]."
