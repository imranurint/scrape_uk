"""
config/settings.py
──────────────────
Single source of truth for all Scrapy settings.
Values are read from environment variables (via .env) so nothing is hard-coded.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ─── Identity ────────────────────────────────────────────────────────────────
BOT_NAME = "uk_uni_scraper"
SPIDER_MODULES = ["scrapers.universities"]
NEWSPIDER_MODULE = "scrapers.universities"

# Polite user-agent (identify the bot honestly)
USER_AGENT = (
    "UKUniScraper/1.0 (+https://github.com/your-org/uk-uni-scraper; "
    "research-bot; respectful-crawl)"
)

# ─── Async reactor (REQUIRED for scrapy-playwright) ──────────────────────────
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

# ─── Download handlers — route http/https through Playwright ─────────────────
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

# ─── Playwright browser options ───────────────────────────────────────────────
PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,
    "args": [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-blink-features=AutomationControlled",
    ],
}
# Max open pages per browser context (tune per server RAM)
PLAYWRIGHT_MAX_PAGES_PER_CONTEXT = 4
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 30_000   # ms

# ─── Concurrency & Politeness ─────────────────────────────────────────────────
CONCURRENT_REQUESTS = int(os.getenv("SCRAPY_CONCURRENT_REQUESTS", 16))
CONCURRENT_REQUESTS_PER_DOMAIN = 4          # don't hammer one uni
DOWNLOAD_DELAY = float(os.getenv("SCRAPY_DOWNLOAD_DELAY", 1.5))
RANDOMIZE_DOWNLOAD_DELAY = True             # delay ± 50%  (AutoThrottle-friendly)

# AutoThrottle — dynamically adjusts delay based on server latency
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1.0
AUTOTHROTTLE_MAX_DELAY = 30.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0
AUTOTHROTTLE_DEBUG = False

# ─── Retry ────────────────────────────────────────────────────────────────────
RETRY_ENABLED = True
RETRY_TIMES = 4                             # 4 retries → 5 total attempts
RETRY_HTTP_CODES = [429, 500, 502, 503, 504, 520, 521, 522, 524]
RETRY_BACKOFF_BASE = 2.0                    # exponential: 2, 4, 8, 16 s

# ─── Middlewares ──────────────────────────────────────────────────────────────
DOWNLOADER_MIDDLEWARES = {
    # Built-in retry (keep enabled)
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": 550,
    # Custom proxy rotation (disabled when PROXY_LIST is empty)
    "scrapers.middlewares.RotatingProxyMiddleware": 610,
    # Custom structured logger
    "scrapers.middlewares.StructuredLoggingMiddleware": 900,
}

SPIDER_MIDDLEWARES = {
    "scrapy.spidermiddlewares.depth.DepthMiddleware": 900,
}

# ─── Pipelines ────────────────────────────────────────────────────────────────
# Lower number = runs first
ITEM_PIPELINES = {
    "pipelines.validation.ValidationPipeline": 100,
    "pipelines.normalisation.NormalisationPipeline": 200,
    "pipelines.duplicates.DuplicatesPipeline": 300,
    "pipelines.database.DatabasePipeline": 400,
}

# ─── Cache (dev-friendly; disable in production scrape runs) ─────────────────
HTTPCACHE_ENABLED = False
HTTPCACHE_EXPIRATION_SECS = 3600
HTTPCACHE_DIR = ".scrapy/httpcache"
HTTPCACHE_IGNORE_HTTP_CODES = [429, 500, 502, 503]

# ─── Logging ─────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("SCRAPY_LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"

# ─── Misc ─────────────────────────────────────────────────────────────────────
ROBOTSTXT_OBEY = True                       # respect robots.txt
COOKIES_ENABLED = True
TELNETCONSOLE_ENABLED = False

# Proxy list read from environment (comma-separated URLs)
PROXY_LIST = [
    p.strip()
    for p in os.getenv("PROXY_LIST", "").split(",")
    if p.strip()
]
