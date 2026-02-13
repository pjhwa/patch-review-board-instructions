# OS Patch Advisory Automation Research

This directory contains the implementation of an automated OS patch advisory collection system for Red Hat Enterprise Linux (RHEL), Oracle Linux (UEK), and Ubuntu LTS distributions.

## Purpose

Replace manual vendor website searches with **reliable, automated batch collection** covering specified time periods (e.g., Nov 2025 - Feb 2026).

## Contents

### Documentation
- **`DEVELOPMENT_LOG.md`**: Comprehensive development history, technical decisions, and script evolution (v1→v8)
- **`INSTALL_PLAYWRIGHT_SKILL_LINUX.md`**: Step-by-step guide for installing Playwright on Linux servers
- **`README.md`**: This file

### Scripts
- **`batch_collector.js`**: Unified collection script for all 3 vendors (latest version)
  - **Red Hat**: Web scraping with pagination (10 pages, date-filtered)
  - **Oracle**: Mailing list archive parsing (trusted feed)
  - **Ubuntu**: Web scraping with LTS filtering (30 pages, date-filtered)

### Utilities
- **`apply_openclaw_fix_v7.sh`**: OpenClaw Gateway port shift + proxy fix for Playwright skill execution

## Quick Start

### Prerequisites
- Linux server with Node.js v22+
- Playwright installed (`npm install playwright`)
- OpenClaw Gateway (if using OpenClaw ecosystem)

### Running Collection

```bash
# On Linux server (e.g., tom26)
cd ~/.openclaw/workspace
npm install playwright
npx playwright install
sudo npx playwright install-deps

# Run batch collector
node batch_collector.js

# Results will be saved to batch_data/ directory
# - RHSA-*.json (Red Hat)
# - ELSA-*.json (Oracle)
# - USN-*.json (Ubuntu)
```

### Configuration

Edit `batch_collector.js` to adjust:
- `TARGET_START_DATE` and `TARGET_END_DATE`: Collection period
- `UBUNTU_LTS_VERSIONS`: Target Ubuntu LTS versions (default: 22.04, 24.04)
- `MAX_REDHAT_PAGES`, `MAX_UBUNTU_PAGES`: Pagination limits
- `MAX_CONCURRENCY`: Parallel browser instances

## Collection Strategy

| Vendor | Method | Source | Reliability |
|--------|--------|--------|-------------|
| **Red Hat** | Web Scraping | `access.redhat.com/errata-search` | High |
| **Oracle** | Mailing List Parsing | `oss.oracle.com/pipermail/el-errata` | Very High |
| **Ubuntu** | Web Scraping | `ubuntu.com/security/notices` | High |

### Why These Methods?

- **Red Hat**: Official errata search with robust pagination (date-sorted, early termination)
- **Oracle**: Official announcement channel (immune to UI changes, static HTML)
- **Ubuntu**: Pagination + post-collection LTS filtering (RSS feeds incomplete)

## Typical Results

For a 3-month period (Nov 2025 - Feb 2026):
- **Red Hat**: ~250 advisories
- **Oracle UEK**: ~60 advisories
- **Ubuntu LTS**: ~50-100 advisories (22.04 + 24.04)

**Total**: ~300-400 unique security advisories

## OpenClaw Integration

If using OpenClaw, apply the gateway fix first:
```bash
bash apply_openclaw_fix_v7.sh
# This shifts the gateway from port 21000→21100 and creates a reverse proxy
```

## Next Steps

After collection:
1. Download `batch_data/` directory
2. Filter for "Critical/Important" severity levels
3. Generate final patch recommendation report

## Technical Stack

- **Runtime**: Node.js v22
- **Automation**: Playwright (headless Chromium)
- **Concurrency**: 3 parallel browsers (configurable)
- **Output**: JSON files (one per advisory)

## Revision History

- **2026-02-13**: Initial release with v8 batch_collector.js
  - Red Hat: 10-page pagination with date-based early termination
  - Oracle: Mailing list archive parsing
  - Ubuntu: Web scraping (replaced RSS feed approach)

## Support

For detailed technical background, strategic decisions, and troubleshooting, see `DEVELOPMENT_LOG.md`.
