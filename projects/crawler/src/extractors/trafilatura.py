# -*- coding: utf-8 -*-
"""
Trafilatura Extractor - uses trafilatura library for content extraction
"""
from typing import Dict
import trafilatura

from .base import BaseExtractor


class TrafilaturaExtractor(BaseExtractor):
    """Universal content extractor using Trafilatura library"""
    
    priority = 10  # Low priority - fallback option
    supported_domains = []  # Universal - matches all
    
    MIN_CONTENT_LENGTH = 50
    
    def extract(self, url: str, html: str) -> Dict:
        # Use trafilatura to extract content
        content = trafilatura.extract(html)
        
        if not content:
            return {
                "url": url,
                "title": "",
                "content": "",
                "type": "generic",
                "error": "No content extracted"
            }
        
        # Extract metadata
        metadata = trafilatura.extract_metadata(html)
        
        title = ""
        author = ""
        publish_date = ""
        if metadata:
            title = getattr(metadata, 'title', '') or ''
            author = getattr(metadata, 'author', '') or ''
            publish_date = getattr(metadata, 'date', '') or ''
        
        return {
            "url": url,
            "title": title,
            "content": content,
            "author": author,
            "publish_date": publish_date,
            "type": "article"
        }
