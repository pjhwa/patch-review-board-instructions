# Patch Review Board (PRB) Automation Research

This folder contains the latest research and tools for automating the quarterly OS Patch Review Board (PRB) process using AI Agents.

## Overview

The goal is to transition from a manual review process to an AI-driven one. This updated workflow (Iteration 4) introduces **Strict Pruning** and **Aggregation** logic to prepare high-quality data for a "Real LLM Review".

## Workflow Components

1.  **Collection**: `batch_collector.js` (Node.js/Playwright)
    -   Scrapes Red Hat, Oracle Linux (Mailing List), and Ubuntu (Web) for advisories.
    -   Outputs JSON files to `batch_data/`.

2.  **Preprocessing**: `patch_preprocessing.py` (Python)
    -   **Pruning**: Strictly whitelists Core System Components (kernel, glibc, systemd) and blacklists applications (firefox, thunderbird).
    -   **Aggregation**: Groups multiple patches for the same component in the quarter. Merges historical impacts into the latest patch description.
    -   **Output**: Generates `patches_for_llm_review.json` for the Agent.

3.  **Agent Execution**:
    -   The AI Agent reads `patches_for_llm_review.json`.
    -   It performs a semantic analysis of the `full_text` and `history` to determine **Critical System Impact** (Hang, Crash, Data Loss, RCE).
    -   It generates the final `patch_review_final_report.csv`.

## Usage Instructions (for AI Agents)

### Step 1: Install Dependencies
```bash
npm install playwright
pip install -r requirements.txt # (if applicable)
```

### Step 2: Run Collection taking ~10 mins
```bash
node batch_collector.js
```

### Step 3: Run Preprocessing
```bash
python patch_preprocessing.py
```
*This generates `patches_for_llm_review.json`.*

### Step 4: LLM Review & Reporting
**Agent Task:**
1.  Read `patches_for_llm_review.json`.
2.  Evaluate each candidate against the **Critical System Impact** criteria:
    -   *Include*: System Hang, Kernel Panic, Data Corruption, Boot Failure, Critical Security (Root/RCE).
    -   *Exclude*: Minor bug fixes, local DoS, application updates.
3.  Write the final report to `patch_review_final_report.csv` with the following columns:
    -   `Category`, `Release Date`, `Vendor`, `Model / Version`, `Detailed Version`, `Patch Name`, `Patch Target`, `Reference Site`, `Patch Description`, `한글 설명`
