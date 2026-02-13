const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// --- CONFIGURATION ---
const OUTPUT_DIR = path.join(__dirname, 'batch_data');
const TARGET_START_DATE = new Date('2025-11-01');
const TARGET_END_DATE = new Date('2026-03-01'); // Exclusive
const ORACLE_TARGET_MONTHS = ['2025-November', '2025-December', '2026-January', '2026-February'];
const UBUNTU_LTS_VERSIONS = ['22.04', '24.04'];
const MAX_CONCURRENCY = 3;
const MAX_REDHAT_PAGES = 10;
const MAX_UBUNTU_PAGES = 30; // Conservative upper limit (~300 notices to check)

if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
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

        await processInBatches(browser, allAdvisories, async (ctxPage, adv) => {
            try {
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
            } catch (e) {
                console.error(`[REDHAT] Failed ${adv.id}: ${e.message}`);
            }
        });

    } catch (e) {
        console.error('[REDHAT] Critical:', e);
    } finally {
        await page.close();
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

        await processInBatches(browser, allAdvisories, async (ctxPage, adv) => {
            try {
                await ctxPage.goto(adv.url, { waitUntil: 'domcontentloaded', timeout: 30000 });
                const details = await ctxPage.evaluate(() => {
                    const pre = document.querySelector('pre');
                    if (pre) return { full_text: pre.innerText };
                    return { full_text: document.body.innerText.replace(/\s+/g, ' ').slice(0, 5000) };
                });
                saveAdvisory(adv.id, { ...adv, ...details, vendor: 'Oracle' });
            } catch (e) {
                console.error(`[ORACLE] Failed ${adv.id}`);
            }
        });

    } catch (e) {
        console.error('[ORACLE] Error:', e);
    } finally {
        await page.close();
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
        await processInBatches(browser, allAdvisories, async (ctxPage, adv) => {
            try {
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

            } catch (e) {
                console.error(`[UBUNTU] Failed ${adv.id}: ${e.message}`);
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
async function processInBatches(browser, items, asyncWorker) {
    const chunks = [];
    for (let i = 0; i < items.length; i += MAX_CONCURRENCY) {
        chunks.push(items.slice(i, i + MAX_CONCURRENCY));
    }
    console.log(`[BATCH] Processing ${items.length} items...`);
    let count = 0;
    for (const chunk of chunks) {
        await Promise.all(chunk.map(async (item) => {
            const context = await browser.newContext();
            const page = await context.newPage();
            await page.route('**/*.{png,jpg,jpeg,gif,svg,woff,woff2,css}', route => route.abort());
            try { await asyncWorker(page, item); }
            finally { await page.close(); await context.close(); }
        }));
        count += chunk.length;
        process.stdout.write(`\r[PROGRESS] ${count}/${items.length}`);
    }
    console.log('\n[BATCH] Done.');
}

// --- MAIN ---
(async () => {
    console.log(`=== BATCH COLLECTOR v8 (Ubuntu Web Scraping Edition) START ===`);
    const browser = await chromium.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    try {
        await scrapeRedHat(browser);
        await scrapeOracleMailingList(browser);
        await scrapeUbuntuWeb(browser);
    } finally {
        await browser.close();
        console.log('=== COLLECTION COMPLETE ===');
    }
})();
