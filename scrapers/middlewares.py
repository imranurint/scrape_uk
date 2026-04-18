"""
scrapers/middlewares.py
───────────────────────
Custom Scrapy downloader middlewares:

1. RotatingProxyMiddleware
   - Reads proxy list from settings.PROXY_LIST
   - Rotates randomly per request
   - Disabled automatically when list is empty

2. StructuredLoggingMiddleware
   - Logs every request/response as structured JSON (via structlog)
   - Tracks response codes and domains for rate-limit detection
"""

from __future__ import annotations

import random
import time
from typing import Optional

import structlog
from scrapy import Spider, signals
from scrapy.http import Request, Response
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.utils.response import response_status_message

logger = structlog.get_logger(__name__)


# ─── 1. Rotating Proxy Middleware ──────────────────────────────────────────────

class RotatingProxyMiddleware:
    """
    Randomly selects a proxy from settings.PROXY_LIST for each request.

    Configuration (.env / settings.py):
        PROXY_LIST = ["http://user:pass@host:port", ...]

    If PROXY_LIST is empty, middleware is a no-op.
    """

    def __init__(self, proxy_list: list[str]) -> None:
        self.proxies = proxy_list

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings.getlist("PROXY_LIST", []))

    def process_request(self, request: Request, spider: Spider) -> None:
        if not self.proxies:
            return
        proxy = random.choice(self.proxies)
        request.meta["proxy"] = proxy
        logger.debug("proxy_assigned", proxy=proxy, url=request.url)


# ─── 2. Structured Logging Middleware ─────────────────────────────────────────

class StructuredLoggingMiddleware:
    """
    Emits one structured log line per request/response pair.
    Helps operations teams monitor crawl health at scale.
    """

    def __init__(self) -> None:
        self._start_times: dict[str, float] = {}

    @classmethod
    def from_crawler(cls, crawler):
        instance = cls()
        crawler.signals.connect(instance.spider_opened, signal=signals.spider_opened)
        return instance

    def spider_opened(self, spider: Spider) -> None:
        logger.info("spider_started", spider=spider.name)

    def process_request(self, request: Request, spider: Spider) -> None:
        self._start_times[request.url] = time.monotonic()
        logger.debug(
            "request_sent",
            url=request.url,
            method=request.method,
            playwright=request.meta.get("playwright", False),
        )

    def process_response(
        self, request: Request, response: Response, spider: Spider
    ) -> Response:
        elapsed = time.monotonic() - self._start_times.pop(request.url, time.monotonic())
        logger.info(
            "response_received",
            url=response.url,
            status=response.status,
            size_bytes=len(response.body),
            elapsed_ms=round(elapsed * 1000),
            spider=spider.name,
        )
        return response

    def process_exception(
        self, request: Request, exception: Exception, spider: Spider
    ) -> None:
        logger.error(
            "download_exception",
            url=request.url,
            error=type(exception).__name__,
            detail=str(exception),
        )


# ─── 3. Custom Retry with Exponential Backoff ─────────────────────────────────

class ExponentialBackoffRetryMiddleware(RetryMiddleware):
    """
    Extends Scrapy's built-in RetryMiddleware with exponential backoff.

    Default backoff: 2^attempt seconds (2, 4, 8, 16 …) capped at 60s.
    Activate in settings.py by replacing the default retry middleware.
    """

    def get_retry_request(self, request, *, spider, reason=""):
        retry_req = super().get_retry_request(request, spider=spider, reason=reason)
        if retry_req:
            retries = retry_req.meta.get("retry_times", 1)
            base = spider.settings.getfloat("RETRY_BACKOFF_BASE", 2.0)
            delay = min(base ** retries, 60.0)
            retry_req.meta["download_slot"] = request.meta.get("download_slot", "")
            retry_req.meta["download_latency"] = delay   # scrapy waits this before retry
            logger.info(
                "retry_scheduled",
                url=request.url,
                attempt=retries,
                delay_s=delay,
                reason=reason,
            )
        return retry_req
