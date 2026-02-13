# OS Patch Advisory Automation - Development Log

## Context

This document tracks the implementation of an automated OS patch advisory collection system for Red Hat Enterprise Linux (RHEL), Oracle Linux (UEK), and Ubuntu LTS distributions. The goal is to replace manual vendor website searches with reliable, automated batch collection covering a 3-month window (Nov 2025 - Feb 2026).

---

## Technical Background

### Initial Challenge: Search Query Limitations

The original `PRB_Instruction-Linux.md` relied on web search queries to find patches. This approach had critical flaws:
- **Unreliable Indexing**: Search engines don't index all vendor advisory pages consistently
- **Rate Limiting**: Frequent searches trigger anti-bot measures
- **Incomplete Coverage**: Recent advisories often missing from search results
- **No Temporal Control**: Cannot reliably filter by publication date ranges

### Solution: Batch Processing Strategy

Instead of search queries, we implemented **direct vendor source parsing**:
- **Red Hat**: Paginated web scraping of errata search (10 pages, date-filtered)
- **Oracle**: Official mailing list archive parsing (`oss.oracle.com/pipermail/el-errata`)
- **Ubuntu**: Web scraping of security notices (30 pages, LTS-filtered)

---

## Infrastructure Setup

### OpenClaw Gateway Fix (v7)

**Problem**: OpenClaw Gateway bound only to `localhost`, preventing external Playwright skill execution.

**Solution**: Port Shift + Proxy Strategy
```bash
# apply_openclaw_fix_v7.sh
ORIGINAL_PORT=21000
NEW_PORT=21100
# Shifts gateway to 21100, creates reverse proxy at 21000
```

**Validation**: `curl http://localhost:21000/health` → `{"status":"healthy"}`

### Playwright Skill Installation

**Platform**: Linux (tom26 server)
**Method**: Direct npm installation (bypassing broken `oc skill` CLI)

```bash
# Installation Steps (INSTALL_PLAYWRIGHT_SKILL_LINUX.md)
cd ~/.openclaw/workspace
npm init -y
npm install playwright
npx playwright install
sudo npx playwright install-deps  # System dependencies
```

**Verification**:
```bash
node -e "const {chromium} = require('playwright'); (async()=>{const b=await chromium.launch(); await b.close();})()"
```

---

## Batch Collector Script Evolution

### v1-v3: Initial Prototypes
- Basic Red Hat scraping (2 pages only)
- Oracle dynamic website attempts (failed due to APEX timeouts)

### v4: Oracle Debugging Phase
- Created `debug_oracle.js` to inspect Oracle security page
- Discovered main page links to version-specific APEX applications
- Dynamic scraping proved unreliable (networkidle timeouts)

### v5: Oracle Mailing List Pivot ✅

**Strategic Decision**: Switched to "Trusted Feed" approach for Oracle.

**Source**: Official Oracle Linux Errata Mailing List Archive
- URL: `https://oss.oracle.com/pipermail/el-errata/`
- Structure: Monthly archives (`2025-November/date.html`, etc.)
- Filtering: Subject lines containing "Unbreakable Enterprise Kernel" (UEK)

**Implementation**:
```javascript
// Iterate through target months
for (const month of ['2025-November', '2025-December', '2026-January', '2026-February']) {
    const url = `${baseUrl}/${month}/date.html`;
    // Parse <li><a> elements, filter for "UEK" in subject
    // Extract ELSA-YYYY-NNNN IDs
}
```

**Result**: **64 UEK advisories** collected

**Advantages**:
- Official announcement channel (high reliability)
- Static HTML (no JavaScript rendering issues)
- Immune to website redesigns

### v6: Red Hat Coverage Expansion ✅

**Problem Identified**: User noticed 47 Red Hat advisories for 3 months was suspiciously low.

**Root Cause**: Script hardcoded to only 2 pages (200 advisories max), but most were from Feb 2026 only.

**Solution**: Date-Smart Pagination
- Increased from 2 → **10 pages** (1,000 advisory capacity)
- Implemented **early termination**: Stop when encountering advisories before `2025-11-01`
- Filtering logic: Only save advisories within target date range

**Implementation**:
```javascript
const MAX_REDHAT_PAGES = 10;
const TARGET_START_DATE = new Date('2025-11-01');

for (let i = 1; i <= MAX_REDHAT_PAGES && shouldContinue; i++) {
    // ... fetch page ...
    const oldestDate = parseDate(pageAdvisories[pageAdvisories.length - 1].dateStr);
    if (oldestDate < TARGET_START_DATE) {
        console.log(`Stopping pagination - reached ${TARGET_START_DATE}`);
        shouldContinue = false;
    }
}
```

**Result**: **255 Red Hat advisories** (5x increase from 47)

### v7: Ubuntu RSS Addition ⚠️

**Initial Approach**: Ubuntu provides official RSS feed at `https://ubuntu.com/security/notices/rss.xml`

**Implementation**:
- Fetched RSS XML, extracted `<item>` elements
- Filtered by LTS version mentions (22.04, 24.04)
- Applied date range filter (Nov 2025 - Feb 2026)

**Result**: **8 Ubuntu advisories** (suspiciously low)

**Discovery**: RSS feed only contains **latest 10 items total**, not the full 3-month archive.

### v8: Ubuntu Web Scraping (Current) 🔄

**Problem**: User correctly identified 8 Ubuntu advisories for 3 months was too low.

**Investigation**:
- Ubuntu Security Notices site: `https://ubuntu.com/security/notices`
- Total advisories available: **10,263**
- Pagination: `?offset=0` (page 1), `?offset=10` (page 2), etc.

**Solution**: Pagination-Based Web Scraping (similar to Red Hat)

**Implementation**:
```javascript
const MAX_UBUNTU_PAGES = 30; // ~300 USN entries

for (let i = 0; i < MAX_UBUNTU_PAGES && shouldContinue; i++) {
    const offset = i * 10;
    const url = `${baseUrl}?offset=${offset}`;
    
    // Extract USN-YYYY-NNNN links
    // Check oldest date on page for early termination
    // Fetch full details for each USN
    // Filter by LTS version (22.04, 24.04) in content
    // Filter by publication date (Nov 2025 - Feb 2026)
}
```

**Status**: Currently executing on tom26 (v8 script in progress)

**Expected Result**: Significantly more than 8 advisories (likely 50-100+ LTS advisories)

---

## Collection Results (Current State)

### Confirmed Results (v7)
- **Red Hat**: 255 advisories (Nov 2025 - Feb 2026)
- **Oracle UEK**: 64 advisories (Mailing List)
- **Ubuntu LTS**: 8 advisories (RSS - acknowledged as incomplete)

### In Progress (v8)
- **Ubuntu LTS**: Web scraping execution ongoing (expected: 50-100+ advisories)

### Final Strategy Summary

| Vendor | Method | Source | Reliability | Notes |
|--------|--------|--------|-------------|-------|
| **Red Hat** | Web Scraping | `access.redhat.com/errata-search` | High | Pagination with date-based early termination |
| **Oracle** | Mailing List Parsing | `oss.oracle.com/pipermail/el-errata` | Very High | Official announcement channel (trusted feed) |
| **Ubuntu** | Web Scraping | `ubuntu.com/security/notices` | High | Pagination + LTS filtering (replaced RSS) |

---

## Key Learnings & Design Decisions

### 1. Trusted Feeds > Dynamic Scraping

**Oracle Case Study**: Instead of scraping complex APEX applications, we parse the official mailing list archive. This is:
- More reliable (static HTML)
- Officially maintained
- Immune to UI changes

### 2. Date-Based Early Termination

**Red Hat & Ubuntu**: Instead of blindly scraping all pages, we:
- Sort by publication date (descending)
- Stop when encountering advisories before target start date
- Reduces unnecessary processing and API load

### 3. LTS Version Filtering

**Ubuntu Strategy**: 
- Collect broadly from pagination
- Filter for LTS versions (22.04, 24.04) in full advisory text
- Ensures we don't miss advisories that affect multiple versions

### 4. RSS Feeds Are Incomplete

**Lesson Learned**: RSS feeds often only contain recent items (10-20), not full archives. Always verify feed depth before relying on it for historical data.

---

## File Artifacts

### Scripts
- `batch_collector.js` (v8): Unified collection for all 3 vendors
- `debug_oracle.js`: Oracle page debugging utility
- `probe_redhat_pages.js`: Red Hat pagination analyzer
- `probe_ubuntu_page.js`: Ubuntu page structure analyzer

### Documentation
- `INSTALL_PLAYWRIGHT_SKILL_LINUX.md`: Playwright setup guide for Linux
- `apply_openclaw_fix_v7.sh`: OpenClaw Gateway port shift fix

### Data
- `batch_data/`: Directory containing collected JSON files (RHSA-*.json, ELSA-*.json, USN-*.json)
- `batch_data_v6.tar.gz`: Red Hat + Oracle collection (279 files)
- `batch_data_v7_all_vendors.tar.gz`: Red Hat + Oracle + Ubuntu RSS (287 files)
- `batch_data_v8_all_vendors.tar.gz`: (In progress) Red Hat + Oracle + Ubuntu Web Scraping

---

## Next Steps

1. **Complete v8 Execution**: Wait for Ubuntu web scraping to finish
2. **Verify Ubuntu Count**: Confirm significantly higher than 8 advisories
3. **Data Analysis**: Filter collected advisories for "Critical/Important" severity
4. **Final Report**: Generate comprehensive patch recommendation list for Nov 2025 - Feb 2026

---

## Technical Stack

- **Runtime**: Node.js v22
- **Automation**: Playwright (headless Chromium)
- **Platform**: Linux (tom26 server)
- **Concurrency**: 3 parallel browsers (configurable)
- **Output**: JSON files (one per advisory)

---

## Revision History

- **2026-02-13 06:00** - Initial log (v1-v5 documentation)
- **2026-02-13 15:30** - Added v6 (Red Hat expansion) and v7 (Ubuntu RSS)
- **2026-02-13 15:56** - Added v8 (Ubuntu web scraping pivot), finalized strategy table
