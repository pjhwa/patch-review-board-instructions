# 🛡️ OS Patch Review Board Automation

> **Automated Security Advisory Collection, Analysis, and Reporting Pipeline**

This project provides a fully automated workflow to replace manual OS patch reviews. It harvests security advisories from vendor sources, filters them through a critical infrastructure lens, and uses AI to generate decision-ready review reports.

## 🚀 Key Features

*   **Multi-Vendor Harvesting**: Automated scraping for **Red Hat** (Portal), **Oracle Linux** (Mailing Lists), and **Ubuntu LTS** (USN Notices).
*   **Intelligent Preprocessing**:
    *   **Whitelist/Blacklist**: Automatically excludes non-essential packages (desktop apps, games) and focuses on Core Infra (Kernel, glibc, systemd, container runtimes).
    *   **Contextual Parsing**: Extracts exact `dist_version` (e.g., distinguishing RHEL 9 from OpenShift) and handles complex versioning logic.
    *   **Aggregation**: Groups multiple updates for the same component to present a unified "latest state" view.
*   **AI-Powered Analysis**: A specialized AI Skill (`SKILL_PatchReviewBoard.md`) analyzes semantic failure modes (System Hang, Data Loss, RCE) and generates bilingual (Korean/English) impact reports.

## 📂 Project Structure

| File | Description |
|---|---|
| `batch_collector.js` | **Collector**. Node.js + Playwright script to scrape raw advisories. |
| `patch_preprocessing.py` | **Refiner**. Python script to filter, dedupe, and aggregate raw data. |
| `SKILL_PatchReviewBoard.md` | **Brain**. The AI Agent Skill definition for review logic and reporting. |
| `GUIDE.md` | **[Deep Dive]**. Detailed architecture and logic explanation. |
| `batch_data/` | **Storage**. Directory where raw JSONs are saved. |

## ⚡ Quick Start

### Prerequisites
*   **Node.js** (v18+) & **Playwright**
*   **Python** (v3.9+)

### 1. Collect Data
Run the headless browser collector to harvest the latest advisories:
```bash
npm install playwright
node batch_collector.js
```

### 2. Preprocess
Clean and aggregate the data into a review packet:
```bash
python patch_preprocessing.py
```
*Output: `patches_for_llm_review.json`*

### 3. AI Review (Simulation)
Use an AI Agent with the defined skill to generate the final CSV:
```python
# The agent reads SKILL_PatchReviewBoard.md and processes the JSON.
# Output: patch_review_final_report.csv
```

## 📖 Documentation
For a deep dive into the architecture, filtering logic, and data flow, please read the **[Automation Research Guide](GUIDE.md)**.
