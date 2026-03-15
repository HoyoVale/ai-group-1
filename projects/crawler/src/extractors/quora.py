# -*- coding: utf-8 -*-
"""
Quora Extractor
"""
import re
from typing import Dict, List
from bs4 import BeautifulSoup

from .base import BaseExtractor


class QuoraExtractor(BaseExtractor):
    """Quora Q&A platform extractor"""
    
    priority = 70
    supported_domains = ["quora.com"]
    
    MIN_CONTENT_LENGTH = 50
    
    def extract(self, url: str, html: str) -> Dict:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Check for security verification
        if "security" in html.lower() or "verification" in html.lower():
            return {
                "url": url,
                "title": soup.find("title").get_text(strip=True) if soup.find("title") else "Quora",
                "content": "",
                "type": "blocked",
                "error": "Security verification required"
            }
        
        title = self._extract_title(soup)
        content = self._extract_content(soup)
        
        return {
            "url": url,
            "title": title,
            "content": content,
            "type": "question"
        }
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        # Try to find question title
        title_elem = soup.find("h1") or soup.find("span", class_=re.compile(r"q-text"))
        if title_elem:
            return title_elem.get_text(strip=True)
        return ""
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        # Find answer content
        content = ""
        
        # Try different selectors for Quora answers
        for selector in ["div.q-text", "span.q-text", "div.answer-content"]:
            elems = soup.find_all(class_=re.compile(r"answer|content"))
            if elems:
                content = "\n".join([e.get_text(strip=True) for e in elems[:3]])
                if content:
                    break
        
        return content[:2000] if content else ""
