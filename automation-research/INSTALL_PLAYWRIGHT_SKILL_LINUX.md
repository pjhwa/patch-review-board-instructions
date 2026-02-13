# 🛠️ OpenClaw Playwright Scraping Skill Installation Guide (Linux)

This guide details how to install the `playwright-scraper` skill on your Linux server (`tom26`) to enable dynamic website batch processing.

## 1. Search for the Skill
First, verify the exact name of the scraping skill available in the ClawHub registry.

```bash
# Run on your Linux server
oc skill search scraper
```
*Look for names like `playwright-scraper` or `web-scraper`.*

## 2. Install the Skill
Assuming the skill name is `playwright-scraper` (replace if the search result is different):

```bash
oc skill install playwright-scraper
```

## 3. Install Browser Binaries (Critical Step)
Playwright requires the actual browser binaries (Chromium, Firefox, WebKit) to be installed on the system. The skill installation via `oc` might not automate this.

```bash
# Go to the OpenClaw data directory (or where `node_modules` are managed)
cd ~/.openclaw

# Install required browsers
npx playwright install --with-deps
```
*Note: The `--with-deps` flag automatically installs necessary OS-level dependencies (libraries, fonts).*

## 4. Restart OpenClaw Service
For the new skill to be loaded by the gateway, restart the service.

```bash
systemctl --user restart openclaw
```

## 5. Verification
Check if the skill is successfully loaded.

```bash
# 1. Check skill list
oc skill list

# 2. Check logs for any startup errors related to Playwright
journalctl --user -u openclaw -n 50 --no-pager
```

---

### 🛑 Troubleshooting "Missing Dependencies"
If you see errors like `libgbm.so.1: cannot open shared object file`, it means OS libraries are missing. Run this command to install them:

```bash
sudo npx playwright install-deps
```
