const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// --- ROBUST DEBUGGING (Anti-Hang) ---
process.on('uncaughtException', (err) => {
    console.error(`\n[FATAL] Uncaught Exception: ${err.message}\n${err.stack}`);
    fs.appendFileSync('debug_collector.log', `[FATAL] Uncaught Exception: ${err.message}\n`);
    saveFailureReport();
    process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
    console.error(`\n[FATAL] Unhandled Rejection at:`, promise, 'reason:', reason);
    fs.appendFileSync('debug_collector.log', `[FATAL] Unhandled Rejection: ${reason}\n`);
});

function logDebug(msg) {
    const ts = new Date().toISOString();
    fs.appendFileSync('debug_collector.log', `[${ts}] ${msg}\n`);
}
logDebug('--- NEW BATCH COLLECTION RUN ---');

// --- CONFIGURATION ---
const OUTPUT_DIR = path.join(__dirname, 'batch_data');
const UBUNTU_LTS_VERSIONS = ['22.04', '24.04'];
const MAX_CONCURRENCY = 3;
const MAX_REDHAT_PAGES = 10;
const MAX_UBUNTU_PAGES = 30;

// --- GLOBAL RETRY CONFIG ---
const MAX_GLOBAL_RETRIES = 2;
const GLOBAL_RETRY_DELAY_MS = 60000; // 60 seconds between retry passes
const RETRY_QUEUE = [];

// --- DATE RANGE: CLI PARSING ---
// Usage:
//   node batch_collector.js --quarter 2026-Q1   → covers quarter + 1-month buffer before
//   node batch_collector.js --days 90           → last 90 days from today
//   node batch_collector.js                     → default: last 90 days
function parseDateRange() {
    const args = process.argv.slice(2);
    let startDate, endDate;

    const quarterIdx = args.indexOf('--quarter');
    const daysIdx = args.indexOf('--days');

    if (quarterIdx !== -1 && args[quarterIdx + 1]) {
        const qMatch = args[quarterIdx + 1].match(/^(\d{4})-Q([1-4])$/);
        if (!qMatch) {
            console.error('Invalid quarter format. Use YYYY-QN (e.g., 2026-Q1)');
            process.exit(1);
        }
        const year = parseInt(qMatch[1]);
        const quarter = parseInt(qMatch[2]);
        // Quarter boundaries: Q1=Jan-Mar, Q2=Apr-Jun, Q3=Jul-Sep, Q4=Oct-Dec
        const qStartMonth = (quarter - 1) * 3; // 0-indexed
        endDate = new Date(year, qStartMonth + 3, 1); // First day of next quarter (exclusive)
        // Buffer: start 1 month before quarter for cumulative patch context
        startDate = new Date(year, qStartMonth - 1, 1);
        console.log(`[CONFIG] Quarter mode: ${args[quarterIdx + 1]}`);
    } else {
        let lookbackDays = 90;
        if (daysIdx !== -1 && args[daysIdx + 1]) {
            lookbackDays = parseInt(args[daysIdx + 1]) || 90;
        }
        endDate = new Date();
        endDate.setDate(endDate.getDate() + 1); // Include today
        startDate = new Date();
        startDate.setDate(startDate.getDate() - lookbackDays);
        startDate.setDate(1); // Snap to first of month
        console.log(`[CONFIG] Lookback mode: ${lookbackDays} days`);
    }

    console.log(`[CONFIG] Date range: ${startDate.toISOString().split('T')[0]} ~ ${endDate.toISOString().split('T')[0]} (exclusive)`);
    return { startDate, endDate };
}

function generateOracleMonths(startDate, endDate) {
    const months = [];
    const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'];
    const current = new Date(startDate.getFullYear(), startDate.getMonth(), 1);
    while (current < endDate) {
        months.push(`${current.getFullYear()}-${monthNames[current.getMonth()]}`);
        current.setMonth(current.getMonth() + 1);
    }
    return months;
}

const { startDate: TARGET_START_DATE, endDate: TARGET_END_DATE } = parseDateRange();
const ORACLE_TARGET_MONTHS = generateOracleMonths(TARGET_START_DATE, TARGET_END_DATE);
console.log(`[CONFIG] Oracle months: ${ORACLE_TARGET_MONTHS.join(', ')}`);

if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

// --- FAILURE TRACKING ---
const failedAdvisories = [];

function recordFailure(vendor, id, url, error) {
    const entry = {
        vendor,
        id: id || 'UNKNOWN',
        url: url || '',
        error: error?.message || String(error),
        timestamp: new Date().toISOString()
    };
    failedAdvisories.push(entry);
    console.error(`[FAILURE] ${vendor} ${entry.id}: ${entry.error}`);
}

function saveFailureReport() {
    if (failedAdvisories.length === 0) {
        console.log('[REPORT] No collection failures.');
        return;
    }
    const filePath = path.join(OUTPUT_DIR, 'collection_failures.json');
    fs.writeFileSync(filePath, JSON.stringify(failedAdvisories, null, 2));
    console.log(`\n[REPORT] ⚠ ${failedAdvisories.length} advisory(ies) failed to collect.`);
    console.log(`[REPORT] Failure details saved to: ${filePath}`);
    console.log('[REPORT] Please review and manually re-collect if needed.');
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// --- UTILS ---
function parseDate(dateStr) {
    if (!dateStr) return new Date(0);
    return new Date(dateStr);
}

function isWithinTargetPeriod(dateObj) {
    return dateObj >= TARGET_START_DATE && dateObj < TARGET_END_DATE;
}

function saveAdvisory(id, data) {
    if (!id) return;
    const safeId = id.replace(/[^a-zA-Z0-9-_]/g, '_');
    const filePath = path.join(OUTPUT_DIR, `${safeId}.json`);
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2));
}

// --- RED HAT SCRAPER (Unchanged) ---
async function scrapeRedHat(browser) {
    console.log('\n[REDHAT] Starting Collector...');
    const page = await browser.newPage();
    const allAdvisories = [];
    let shouldContinue = true;

    try {
        const baseUrl = 'https://access.redhat.com/errata-search/?q=&sort=portal_publication_date%20desc&rows=100&portal_errata_type=Security%20Advisory&portal_product_filter=Red%20Hat%20Enterprise%20Linux';

        for (let i = 1; i <= MAX_REDHAT_PAGES && shouldContinue; i++) {
            const url = `${baseUrl}&p=${i}`;
            console.log(`[REDHAT] Fetching List Page ${i}/${MAX_REDHAT_PAGES}: ${url}`);

            try {
                await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
                try {
                    await page.waitForSelector('.search-result-table tbody tr', { timeout: 15000 });
                } catch (e) {
                    await page.waitForTimeout(5000);
                }

                const pageAdvisories = await page.evaluate(() => {
                    let rows = Array.from(document.querySelectorAll('.search-result-table tbody tr'));
                    if (rows.length === 0) {
                        const links = Array.from(document.querySelectorAll('a[href*="/errata/RHSA"]'));
                        return links.map(link => ({
                            id: link.innerText.trim(),
                            url: link.href,
                            dateStr: new Date().toISOString()
                        }));
                    }
                    return rows.map(row => {
                        const idLink = row.querySelector('td a') || row.querySelector('th a');
                        if (!idLink) return null;
                        const cells = row.querySelectorAll('td');
                        const dateText = cells[cells.length - 1]?.innerText.trim() || '';
                        return {
                            id: idLink.innerText.trim(),
                            url: idLink.href,
                            synopsis: cells[0]?.innerText.trim() || '',
                            dateStr: dateText
                        };
                    }).filter(x => x && x.id.includes('RHSA'));
                });

                if (pageAdvisories.length > 0) {
                    const oldestDate = parseDate(pageAdvisories[pageAdvisories.length - 1].dateStr);
                    if (oldestDate < TARGET_START_DATE) {
                        console.log(`[REDHAT] Page ${i}: Reached advisories before ${TARGET_START_DATE.toISOString().split('T')[0]}. Stopping pagination.`);
                        const filtered = pageAdvisories.filter(adv => parseDate(adv.dateStr) >= TARGET_START_DATE);
                        allAdvisories.push(...filtered);
                        shouldContinue = false;
                        break;
                    }
                }

                allAdvisories.push(...pageAdvisories);

            } catch (err) {
                console.error(`[REDHAT] Error page ${i}: ${err.message}`);
            }
        }

        console.log(`[REDHAT] Found ${allAdvisories.length} candidates across pages.`);

        await processInBatches(browser, allAdvisories, 'Red Hat', async (ctxPage, adv) => {
            await ctxPage.goto(adv.url, { waitUntil: 'domcontentloaded', timeout: 30000 });
            const details = await ctxPage.evaluate(() => {
                const main = document.querySelector('#main-content') || document.body;
                const clones = main.cloneNode(true);
                clones.querySelectorAll('nav, footer, script, style, .hide').forEach(n => n.remove());
                return {
                    full_text: clones.innerText.replace(/\s+/g, ' ').slice(0, 6000),
                    title: document.title
                };
            });
            saveAdvisory(adv.id, { ...adv, ...details, vendor: 'Red Hat' });
        });

    } catch (e) {
        console.error('[REDHAT] Critical:', e);
    } finally {
        try { await page.close(); } catch (_) { }
    }
}

// --- ORACLE MAILING LIST SCRAPER (Unchanged) ---
async function scrapeOracleMailingList(browser) {
    console.log('\n[ORACLE] Starting Collector (Mailing List Archive)...');
    const page = await browser.newPage();
    const allAdvisories = [];

    try {
        const baseUrl = 'https://oss.oracle.com/pipermail/el-errata';

        for (const month of ORACLE_TARGET_MONTHS) {
            const url = `${baseUrl}/${month}/date.html`;
            console.log(`[ORACLE] Fetching Archive: ${url}`);

            try {
                const response = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
                if (response.status() === 404) {
                    console.log(`[ORACLE] Archive for ${month} not found (404). Skipping.`);
                    continue;
                }

                const pageAdvisories = await page.evaluate((monthStr) => {
                    const links = Array.from(document.querySelectorAll('ul li a'));

                    return links.map(link => {
                        const text = link.innerText.trim();
                        if (!text.toLowerCase().includes('unbreakable enterprise kernel')) {
                            return null;
                        }

                        const idMatch = text.match(/EL[SB]A-\d{4}-\d+/);
                        const id = idMatch ? idMatch[0] : `ELSA-UNKNOWN-${Math.random().toString(36).substr(2, 5)}`;

                        return {
                            id: id,
                            url: link.href,
                            synopsis: text,
                            dateStr: monthStr,
                            type: 'Mailing List Announcement'
                        };
                    }).filter(Boolean);
                }, month);

                console.log(`[ORACLE] Found ${pageAdvisories.length} UEK advisories in ${month}.`);
                allAdvisories.push(...pageAdvisories);

            } catch (err) {
                console.error(`[ORACLE] Error fetching ${month}: ${err.message}`);
            }
        }

        console.log(`[ORACLE] Total UEK Candidates: ${allAdvisories.length}`);

        await processInBatches(browser, allAdvisories, 'Oracle', async (ctxPage, adv) => {
            await ctxPage.goto(adv.url, { waitUntil: 'domcontentloaded', timeout: 30000 });
            const details = await ctxPage.evaluate(() => {
                const pre = document.querySelector('pre');
                if (pre) return { full_text: pre.innerText };
                return { full_text: document.body.innerText.replace(/\s+/g, ' ').slice(0, 5000) };
            });
            saveAdvisory(adv.id, { ...adv, ...details, vendor: 'Oracle' });
        });

    } catch (e) {
        console.error('[ORACLE] Error:', e);
    } finally {
        try { await page.close(); } catch (_) { }
    }
}

// --- UBUNTU WEB SCRAPER (New - Pagination-Based) ---
async function scrapeUbuntuWeb(browser) {
    console.log('\n[UBUNTU] Starting Collector (Web Pagination)...');
    const page = await browser.newPage();
    const allAdvisories = [];
    let shouldContinue = true;

    try {
        const baseUrl = 'https://ubuntu.com/security/notices';

        for (let i = 0; i < MAX_UBUNTU_PAGES && shouldContinue; i++) {
            const offset = i * 10;
            const url = `${baseUrl}?offset=${offset}`;
            console.log(`[UBUNTU] Fetching List Page ${i + 1}/${MAX_UBUNTU_PAGES} (offset=${offset}): ${url}`);

            try {
                await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
                await page.waitForTimeout(2000);

                const pageAdvisories = await page.evaluate(() => {
                    const usnLinks = Array.from(document.querySelectorAll('a[href*="/security/notices/USN"]'));

                    return usnLinks.map(link => {
                        const text = link.innerText.trim();
                        const usnMatch = text.match(/USN-\d+-\d+/);
                        if (!usnMatch) return null;

                        // Try to find date from parent row/container
                        let dateStr = '';
                        const row = link.closest('tr, li, .row, .notice-item');
                        if (row) {
                            const dateMatch = row.innerText.match(/(\d{1,2}\s+\w+\s+\d{4})/);
                            if (dateMatch) dateStr = dateMatch[1];
                        }

                        return {
                            id: usnMatch[0],
                            url: link.href,
                            synopsis: text,
                            dateStr: dateStr || ''
                        };
                    }).filter(Boolean);
                });

                console.log(`[UBUNTU] Page ${i + 1}: Found ${pageAdvisories.length} USN entries.`);

                if (pageAdvisories.length === 0) {
                    console.log(`[UBUNTU] No more entries found. Stopping pagination.`);
                    shouldContinue = false;
                    break;
                }

                // Check if we've gone too far back (if dates are available)
                const datedAdvisories = pageAdvisories.filter(adv => adv.dateStr);
                if (datedAdvisories.length > 0) {
                    const oldestDate = parseDate(datedAdvisories[datedAdvisories.length - 1].dateStr);
                    if (oldestDate < TARGET_START_DATE && oldestDate > new Date('2000-01-01')) {
                        console.log(`[UBUNTU] Page ${i + 1}: Reached advisories before target start date. Stopping pagination.`);
                        shouldContinue = false;
                    }
                }

                allAdvisories.push(...pageAdvisories);

            } catch (err) {
                console.error(`[UBUNTU] Error page ${i + 1}: ${err.message}`);
            }
        }

        console.log(`[UBUNTU] Found ${allAdvisories.length} total USN candidates.`);

        // Fetch full details for each and filter by LTS version
        const ltsAdvisories = [];
        await processInBatches(browser, allAdvisories, 'Ubuntu', async (ctxPage, adv) => {
            await ctxPage.goto(adv.url, { waitUntil: 'domcontentloaded', timeout: 30000 });
            const details = await ctxPage.evaluate(() => {
                const main = document.querySelector('main') || document.body;
                const clones = main.cloneNode(true);
                clones.querySelectorAll('nav, footer, script, style, .hide').forEach(n => n.remove());
                const text = clones.innerText.replace(/\s+/g, ' ');

                // Extract publication date
                const dateMatch = text.match(/(\d{1,2}\s+\w+\s+\d{4})/);

                return {
                    full_text: text.slice(0, 6000),
                    title: document.title,
                    pubDate: dateMatch ? dateMatch[1] : ''
                };
            });

            // Filter by LTS version
            const hasTargetLTS = UBUNTU_LTS_VERSIONS.some(ver =>
                details.full_text.includes(ver) || details.full_text.includes(`Ubuntu ${ver}`)
            );

            // Filter by date
            const pubDate = parseDate(details.pubDate || adv.dateStr);
            const inTargetPeriod = isWithinTargetPeriod(pubDate);

            if (hasTargetLTS && inTargetPeriod) {
                saveAdvisory(adv.id, { ...adv, ...details, vendor: 'Ubuntu', pubDate: pubDate.toISOString() });
                ltsAdvisories.push(adv.id);
            }
        });

        console.log(`[UBUNTU] Saved ${ltsAdvisories.length} LTS advisories matching target period.`);

    } catch (e) {
        console.error('[UBUNTU] Error:', e);
    } finally {
        await page.close();
    }
}

// --- HELPER ---
async function processInBatches(browser, items, vendorTitle, asyncWorker) {
    const chunks = [];
    for (let i = 0; i < items.length; i += MAX_CONCURRENCY) {
        chunks.push(items.slice(i, i + MAX_CONCURRENCY));
    }
    console.log(`[BATCH] Processing ${items.length} ${vendorTitle} items...`);
    let count = 0;
    let browserDead = false;
    for (const chunk of chunks) {
        if (browserDead) {
            for (const item of chunk) {
                RETRY_QUEUE.push({ vendor: vendorTitle, item, worker: asyncWorker, error: new Error('Browser closed — skipped remaining items') });
            }
            count += chunk.length;
            continue;
        }
        await Promise.all(chunk.map(async (item) => {
            let context, page;
            try {
                context = await browser.newContext();
                page = await context.newPage();
            } catch (e) {
                browserDead = true;
                RETRY_QUEUE.push({ vendor: vendorTitle, item, worker: asyncWorker, error: new Error(`Browser closed — cannot create page: ${e.message}`) });
                return;
            }
            try {
                await page.route('**/*.{png,jpg,jpeg,gif,svg,woff,woff2,css}', route => route.abort());

                logDebug(`[PROCESS] Starting ${item.id} (${item.url})`);

                const timeoutPromise = new Promise((_, reject) =>
                    setTimeout(() => reject(new Error('WATCHDOG_TIMEOUT: 60000ms exceeded')), 60000)
                );

                await Promise.race([
                    asyncWorker(page, item),
                    timeoutPromise
                ]);

                logDebug(`[PROCESS] Success ${item.id}`);
            } catch (e) {
                if (e.message && e.message.includes('has been closed')) {
                    browserDead = true;
                }
                RETRY_QUEUE.push({ vendor: vendorTitle, item, worker: asyncWorker, error: e });
                logDebug(`[PROCESS FAIL] ${item.id}: ${e.message}`);
            } finally {
                try { if (page) await page.close(); } catch (_) { }
                try { if (context) await context.close(); } catch (_) { }
            }
        }));
        count += chunk.length;
        process.stdout.write(`\r[PROGRESS] ${count}/${items.length}`);
    }
    console.log('\n[BATCH] Done.');
    return browserDead;
}

// --- MAIN ---
(async () => {
    console.log(`=== BATCH COLLECTOR v12 (Robust Debug Edition) START ===`);

    async function launchBrowser() {
        return chromium.launch({
            headless: true,
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        });
    }

    // Run each vendor with its own browser instance for isolation.
    // If one vendor crashes the browser, others still run.
    const vendors = [
        { name: 'Red Hat', fn: scrapeRedHat },
        { name: 'Oracle', fn: scrapeOracleMailingList },
        { name: 'Ubuntu', fn: scrapeUbuntuWeb }
    ];

    for (const { name, fn } of vendors) {
        let browser;
        try {
            browser = await launchBrowser();
            await fn(browser);
        } catch (e) {
            console.error(`[MAIN] ${name} scraper failed: ${e.message}`);
            recordFailure(name, 'SCRAPER_CRASH', '', e);
        } finally {
            try { if (browser) await browser.close(); } catch (_) { }
        }
    }

    // --- GLOBAL RETRY LOGIC ---
    for (let pass = 1; pass <= MAX_GLOBAL_RETRIES; pass++) {
        if (RETRY_QUEUE.length === 0) break;

        console.log(`\n=== GLOBAL RETRY PASS ${pass}/${MAX_GLOBAL_RETRIES} ===`);
        console.log(`Waiting ${GLOBAL_RETRY_DELAY_MS / 1000} seconds before retrying ${RETRY_QUEUE.length} failed items...`);
        await sleep(GLOBAL_RETRY_DELAY_MS);

        const currentQueue = RETRY_QUEUE.splice(0, RETRY_QUEUE.length);
        const chunks = [];
        for (let i = 0; i < currentQueue.length; i += MAX_CONCURRENCY) {
            chunks.push(currentQueue.slice(i, i + MAX_CONCURRENCY));
        }

        let browser;
        try {
            browser = await launchBrowser();
            let browserDead = false;
            let count = 0;

            for (const chunk of chunks) {
                if (browserDead) {
                    for (const retryObj of chunk) {
                        retryObj.error = new Error('Browser closed earlier in retry pass');
                        RETRY_QUEUE.push(retryObj);
                    }
                    count += chunk.length;
                    continue;
                }

                await Promise.all(chunk.map(async (retryObj) => {
                    let context, page;
                    try {
                        context = await browser.newContext();
                        page = await context.newPage();
                    } catch (e) {
                        browserDead = true;
                        retryObj.error = new Error(`Browser context failed: ${e.message}`);
                        RETRY_QUEUE.push(retryObj);
                        return;
                    }

                    try {
                        await page.route('**/*.{png,jpg,jpeg,gif,svg,woff,woff2,css}', route => route.abort());
                        const timeoutPromise = new Promise((_, reject) => setTimeout(() => reject(new Error('WATCHDOG_TIMEOUT')), 60000));

                        await Promise.race([
                            retryObj.worker(page, retryObj.item),
                            timeoutPromise
                        ]);

                        logDebug(`[RETRY SUCCESS] Pass ${pass} - ${retryObj.vendor} ${retryObj.item.id}`);
                    } catch (e) {
                        if (e.message && e.message.includes('has been closed')) {
                            browserDead = true;
                        }
                        retryObj.error = e;
                        RETRY_QUEUE.push(retryObj);
                        logDebug(`[RETRY FAIL] Pass ${pass} - ${retryObj.vendor} ${retryObj.item.id}: ${e.message}`);
                    } finally {
                        try { if (page) await page.close(); } catch (_) { }
                        try { if (context) await context.close(); } catch (_) { }
                    }
                }));
                count += chunk.length;
                process.stdout.write(`\r[RETRY PROGRESS] ${count}/${currentQueue.length}`);
            }
        } catch (e) {
            console.error(`\n[RETRY] Pass ${pass} Browser launch failed: ${e.message}`);
            // Push everything back and abort this pass
            RETRY_QUEUE.push(...currentQueue);
        } finally {
            try { if (browser) await browser.close(); } catch (_) { }
        }
        console.log('');
    }

    console.log('\n[BATCH SUMMARY] Global Retries finished.');

    // Register absolute failures
    const finalFails = Array.from(new Set(RETRY_QUEUE));
    for (const fail of finalFails) {
        recordFailure(fail.vendor, fail.item.id, fail.item.url, fail.error);
    }

    saveFailureReport();
    console.log('=== COLLECTION COMPLETE ===');
})();
