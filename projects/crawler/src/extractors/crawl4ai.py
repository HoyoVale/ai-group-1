# -*- coding: utf-8 -*-
"""
Crawl4AI Extractor - uses Crawl4AI for content extraction
"""
import asyncio
from typing import Dict
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

from .base import BaseExtractor


class Crawl4AIExtractor(BaseExtractor):
    """Content extractor using Crawl4AI library"""
    
    priority = 5  # Lowest priority - fallback
    supported_domains = []  # Universal
    
    MIN_CONTENT_LENGTH = 50
    
    def extract(self, url: str, html: str = None) -> Dict:
        # If we already have HTML, use it; otherwise crawl
        # Note: Crawl4AI works best when crawling fresh URLs
        return {
            "url": url,
            "title": "",
            "content": "",
            "type": "generic",
            "note": "Use crawl4ai directly for best results"
        }
    
    @staticmethod
    async def crawl(url: str) -> Dict:
        """Crawl URL using Crawl4AI"""
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url)
            return {
                "url": url,
                "title": "",
                "content": result.markdown if result.markdown else "",
                "html": result.html if result.html else "",
                "success": result.success if hasattr(result, 'success') else True
            }


def crawl_with_crawl4ai(url: str) -> Dict:
    """Sync wrapper for Crawl4AI"""
    return asyncio.run(Crawl4AIExtractor.crawl(url))
