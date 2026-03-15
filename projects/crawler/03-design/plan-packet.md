# 通用爬虫工具完善 - 架构设计方案

## 任务信息

- **任务ID**: crawler-enhancement
- **方案版本**: v1.0
- **设计角色**: Solin (架构与质量官)
- **仓库路径**: `/home/hoyo/ai-group-1/projects/crawler/`
- **存储路径**: `~/Downloads/crawler/output`
- **生成时间**: 2026-03-15

---

## 1. 约束与边界

### 1.1 技术约束

| 约束项 | 说明 |
|--------|------|
| 语言 | Python 3.10+ |
| 核心依赖 | requests, beautifulsoup4, playwright |
| 存储路径 | Linux 路径 `~/Downloads/crawler/output` (不可改为 Windows) |
| 现有模块 | `BilibiliExtractor`, `GeneralExtractor` 需保留并迁移 |

### 1.2 不可破坏项

- 现有 `get_extractor()` 函数的外部调用接口需保持兼容
- 已实现的 `BilibiliExtractor` 提取逻辑不可删除
- `config.py` 中的基础配置 (OUTPUT_DIR, DEFAULT_TIMEOUT) 不可移除

---

## 2. 提取器架构设计

### 2.1 目录结构

```
src/extractors/
├── __init__.py           # 导出 get_extractor, 兼容旧接口
├── base.py               # BaseExtractor 基类
├── registry.py           # ExtractorRegistry 注册中心
├── general.py            # GeneralExtractor (保留)
├── bilibili.py           # BilibiliExtractor (从 extractors.py 迁移)
├── douyin.py             # 抖音提取器 ⭐ 新增
├── baidu.py              # 百度提取器 ⭐ 新增
├── sohu.py               # 搜狐提取器 ⭐ 新增
├── quark.py              # 夸克提取器 ⭐ 新增
├── wiki.py               # 百科提取器 ⭐ 新增
└── image.py             # ImageExtractor (从 extractors.py 迁移)
```

### 2.2 BaseExtractor 基类接口定义

```python
# src/extractors/base.py
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ExtractionResult:
    """标准化提取结果"""
    # 必需字段
    url: str
    title: str = ""
    content: str = ""
    
    # 可选字段
    images: List[Dict] = field(default_factory=list)
    videos: List[Dict] = field(default_factory=list)
    meta: Dict = field(default_factory=dict)
    
    # 站点特定字段 (动态扩展)
    extra: Dict = field(default_factory=dict)
    
    # 提取元数据
    extracted_at: str = field(default_factory=lambda: datetime.now().isoformat())
    extractor: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "images": self.images,
            "videos": self.videos,
            "meta": self.meta,
            "extra": self.extra,
            "extracted_at": self.extracted_at,
            "extractor": self.extractor
        }


class BaseExtractor(ABC):
    """网站内容提取器基类"""
    
    # === 类属性 ===
    
    # 是否需要 Playwright (JS 渲染)
    NEEDS_JAVASCRIPT: bool = False
    
    # 站点域名模式 (用于匹配)
    DOMAIN_PATTERNS: List[str] = []
    
    # 优先级 (越高越先匹配)
    PRIORITY: int = 0
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
    
    @abstractmethod
    def extract(self, url: str, html: str) -> ExtractionResult:
        """
        提取页面内容
        
        Args:
            url: 页面 URL
            html: HTML 内容
            
        Returns:
            ExtractionResult: 标准化提取结果
        """
        pass
    
    def pre_validate(self, url: str, html: str) -> bool:
        """
        预验证: 确认是否是正确的页面 (可选)
        用于域名匹配后的二次确认
        
        Args:
            url: 页面 URL
            html: HTML 内容
            
        Returns:
            bool: True 如果验证通过
        """
        return True
    
    @classmethod
    def get_extractor_name(cls) -> str:
        """获取提取器名称 (用于日志/调试)"""
        return cls.__name__.replace("Extractor", "")
```

### 2.3 ExtractorRegistry 注册机制

```python
# src/extractors/registry.py
from typing import Dict, Type, List, Tuple, Optional
from urllib.parse import urlparse
import logging

from .base import BaseExtractor, ExtractionResult
from .general import GeneralExtractor


logger = logging.getLogger(__name__)


class ExtractorRegistry:
    """
    提取器注册中心
    
    匹配优先级:
    1. 精确匹配 (exact) - 完整的域名+路径模式
    2. 域名匹配 (domain) - 仅域名部分
    3. 通配符匹配 (wildcard) - 包含特定关键词的 URL
    4. 默认兜底 (default) - GeneralExtractor
    """
    
    # 优先级常量
    PRIORITY_EXACT = 100   # 精确匹配 (如 baidu.com/search)
    PRIORITY_DOMAIN = 50   # 域名匹配 (如 bilibili.com)
    PRIORITY_WILDCARD = 30 # 通配符匹配 (如 .cn 域名)
    PRIORITY_DEFAULT = 0   # 默认兜底
    
    def __init__(self):
        self._extractors: List[Tuple[str, int, str, Type[BaseExtractor]]] = []
        self._initialized = False
    
    def register(
        self, 
        domain_pattern: str, 
        priority: int = PRIORITY_DOMAIN,
        match_type: str = "domain"
    ):
        """
        注册提取器
        
        Args:
            domain_pattern: 域名模式 (如 "douyin.com", "baidu.com/search")
            priority: 优先级 (越高越先匹配)
            match_type: 匹配类型 ("exact", "domain", "wildcard")
        """
        def decorator(cls: Type[BaseExtractor]):
            # 验证类继承自 BaseExtractor
            if not issubclass(cls, BaseExtractor):
                raise TypeError(f"{cls.__name__} must inherit from BaseExtractor")
            
            self._extractors.append((
                domain_pattern.lower(),
                priority,
                match_type,
                cls
            ))
            
            # 按优先级排序 (高优先级在前)
            self._extractors.sort(key=lambda x: x[1], reverse=True)
            
            logger.debug(f"Registered {cls.__name__} for '{domain_pattern}' (priority={priority}, type={match_type})")
            return cls
        
        return decorator
    
    def get_extractor(self, url: str) -> BaseExtractor:
        """
        根据 URL 获取最佳匹配的提取器
        
        Args:
            url: 目标 URL
            
        Returns:
            BaseExtractor: 匹配的提取器实例
        """
        parsed = urlparse(url)
        hostname = parsed.netloc.lower()
        path = parsed.path.lower()
        url_lower = url.lower()
        
        # 按优先级遍历匹配
        for pattern, priority, match_type, cls in self._extractors:
            if self._match(url_lower, hostname, path, pattern, match_type):
                # 如果有 pre_validate, 尝试验证
                instance = cls()
                if hasattr(instance, '_validate_html'):
                    # 尝试快速获取 HTML 进行验证
                    # 注意: 这里不做实际请求，仅记录日志
                    logger.debug(f"{cls.__name__} matched for {url}, validating...")
                
                logger.info(f"Matched extractor: {cls.__name__} for {url}")
                return instance
        
        # 兜底: 返回通用提取器
        logger.info(f"No specific extractor matched, using GeneralExtractor for {url}")
        return GeneralExtractor()
    
    def _match(
        self, 
        url_lower: str, 
        hostname: str, 
        path: str, 
        pattern: str, 
        match_type: str
    ) -> bool:
        """执行匹配逻辑"""
        if match_type == "exact":
            # 精确匹配: 完整 URL 或 域名+路径
            return pattern in url_lower or f"{hostname}{path}".startswith(pattern)
        elif match_type == "domain":
            # 域名匹配: 仅检查域名
            return pattern in hostname
        elif match_type == "wildcard":
            # 通配符匹配: 包含特定关键词
            return pattern in url_lower
        return False
    
    def list_extractors(self) -> List[Dict]:
        """列出所有已注册的提取器"""
        return [
            {
                "pattern": p,
                "priority": pr,
                "match_type": m,
                "class": c.__name__
            }
            for p, pr, m, c in self._extractors
        ]


# 全局注册中心实例
_registry = ExtractorRegistry()


# === 注册装饰器 ===
def register_extractor(
    domain_pattern: str, 
    priority: int = ExtractorRegistry.PRIORITY_DOMAIN,
    match_type: str = "domain"
):
    """注册提取器的便捷装饰器"""
    return _registry.register(domain_pattern, priority, match_type)


def get_extractor(url: str) -> BaseExtractor:
    """获取提取器 (兼容旧接口)"""
    return _registry.get_extractor(url)
```

### 2.4 各站点提取器注册配置

```python
# src/extractors/__init__.py
from .base import BaseExtractor, ExtractionResult
from .registry import _registry, register_extractor, get_extractor
from .general import GeneralExtractor

# === 注册站点提取器 ===

@register_extractor("douyin.com", priority=100, match_type="domain")
class DouyinExtractor(BaseExtractor):
    """抖音视频提取器"""
    NEEDS_JAVASCRIPT = True
    DOMAIN_PATTERNS = ["douyin.com"]
    
    def extract(self, url: str, html: str) -> ExtractionResult:
        # 实现见下文 2.5
        pass

@register_extractor("bilibili.com", priority=100, match_type="domain")
class BilibiliExtractor(BaseExtractor):
    """B站视频提取器"""
    NEEDS_JAVASCRIPT = True
    # 从原 extractors.py 迁移
    pass

@register_extractor("baidu.com", priority=80, match_type="domain")
class BaiduExtractor(BaseExtractor):
    """百度搜索/百科提取器"""
    NEEDS_JAVASCRIPT = False
    pass

@register_extractor("sohu.com", priority=80, match_type="domain")
class SohuExtractor(BaseExtractor):
    """搜狐提取器"""
    NEEDS_JAVASCRIPT = False
    pass

@register_extractor("quark.so.com", priority=80, match_type="domain")
@register_extractor("quark.cn", priority=80, match_type="domain")
class QuarkExtractor(BaseExtractor):
    """夸克搜索提取器"""
    NEEDS_JAVASCRIPT = True  # 需验证是否需要
    pass

# Wiki 类站点
@register_extractor("wikipedia.org", priority=70, match_type="domain")
@register_extractor("baike.baidu.com", priority=70, match_type="domain")
@register_extractor("zhihu.com", priority=70, match_type="domain")
@register_extractor("wikihow.com", priority=70, match_type="domain")
class WikiExtractor(BaseExtractor):
    """百科/Wiki 提取器"""
    NEEDS_JAVASCRIPT = False
    pass

# 图片站点
@register_extractor("unsplash.com", priority=60, match_type="domain")
@register_extractor("pexels.com", priority=60, match_type="domain")
@register_extractor("pixabay.com", priority=60, match_type="domain")
class ImageExtractor(BaseExtractor):
    """图片网站提取器"""
    # 从原 extractors.py 迁移
    pass

# GitHub
@register_extractor("github.com", priority=90, match_type="domain")
@register_extractor("githubusercontent.com", priority=90, match_type="domain")
class GitHubExtractor(BaseExtractor):
    """GitHub 提取器"""
    # 从原 extractors.py 迁移
    pass

# === 导出 ===
__all__ = [
    'BaseExtractor',
    'ExtractionResult', 
    'get_extractor',
    'register_extractor',
    'GeneralExtractor',
]
```

### 2.5 各站点提取器实现要点

#### 2.5.1 抖音提取器 (DouyinExtractor)

```python
class DouyinExtractor(BaseExtractor):
    """抖音视频提取器"""
    
    NEEDS_JAVASCRIPT = True  # 必须使用 Playwright
    DOMAIN_PATTERNS = ["douyin.com", "v.douyin.com"]
    
    def extract(self, url: str, html: str) -> ExtractionResult:
        import re
        import json
        
        result = ExtractionResult(url=url, extractor=self.get_extractor_name())
        
        # 1. 提取标题
        og_title = self._find_meta(html, "og:title")
        if not result.title:
            title_match = re.search(r'"desc":"([^"]+)"', html)
            if title_match:
                result.title = title_match.group(1)
        
        # 2. 提取视频信息
        video_data = self._extract_video_data(html)
        if video_data:
            result.videos.append({
                "url": video_data.get("play_url", ""),
                "cover": video_data.get("cover_url", ""),
                "duration": video_data.get("duration", 0),
                "format": video_data.get("format", "mp4")
            })
        
        # 3. 提取封面图
        og_image = self._find_meta(html, "og:image")
        if og_image:
            result.images.append({"url": og_image, "type": "cover"})
        
        # 4. 提取作者信息
        author_data = self._extract_author(html)
        if author_data:
            result.extra["author"] = author_data
        
        # 5. 提取互动数据
        stats = self._extract_stats(html)
        if stats:
            result.extra["stats"] = stats
        
        return result
    
    def _find_meta(self, html: str, property: str) -> str:
        import re
        pattern = rf'<meta[^>]+property=["\']?{property}["\']?[^>]+content=["\']([^"\']+)["\']'
        match = re.search(pattern, html, re.IGNORECASE)
        return match.group(1) if match else ""
    
    def _extract_video_data(self, html: str) -> Dict:
        import re
        import json
        
        patterns = [
            r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
            r'window\.playInfo\s*=\s*({.*?});',
            r'"videoInfo":\s*({.*?})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    return {
                        "play_url": data.get("playAddr", ""),
                        "cover_url": data.get("cover", {}).get("url", ""),
                        "duration": data.get("duration", 0),
                        "format": "mp4"
                    }
                except:
                    pass
        return {}
    
    def _extract_author(self, html: str) -> Dict:
        import re
        match = re.search(r'"author":\s*{"nickname":"([^"]+)"', html)
        if match:
            return {"nickname": match.group(1)}
        return {}
    
    def _extract_stats(self, html: str) -> Dict:
        import re
        stats = {}
        
        like_match = re.search(r'"diggCount":\s*(\d+)', html)
        if like_match:
            stats["likes"] = int(like_match.group(1))
        
        comment_match = re.search(r'"commentCount":\s*(\d+)', html)
        if comment_match:
            stats["comments"] = int(comment_match.group(1))
        
        return stats
```

#### 2.5.2 百度提取器 (BaiduExtractor)

```python
class BaiduExtractor(BaseExtractor):
    """百度搜索/百科提取器"""
    
    NEEDS_JAVASCRIPT = False  # 搜索结果静态可读
    DOMAIN_PATTERNS = ["baidu.com"]
    
    def pre_validate(self, url: str, html: str) -> bool:
        """区分百度搜索和百度百科"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        
        if "baike.baidu.com" in parsed.netloc:
            self._mode = "baike"
        elif "zhidao.baidu.com" in parsed.netloc:
            self._mode = "zhidao"
        else:
            self._mode = "search"
        
        return True
    
    def extract(self, url: str, html: str) -> ExtractionResult:
        result = ExtractionResult(url=url, extractor=self.get_extractor_name())
        
        if hasattr(self, '_mode') and self._mode == "baike":
            return self._extract_baike(url, html, result)
        elif hasattr(self, '_mode') and self._mode == "zhidao":
            return self._extract_zhidao(url, html, result)
        else:
            return self._extract_search(url, html, result)
    
    def _extract_search(self, url: str, html: str, result: ExtractionResult) -> ExtractionResult:
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'html.parser')
        
        title = soup.find("title")
        result.title = title.get_text(strip=True) if title else ""
        
        for item in soup.select(".result, .c-container"):
            title_elem = item.select_one(".t, .c-title")
            link_elem = item.select_one("a")
            snippet_elem = item.select_one(".c-abstract, .content-right_8Zs40")
            
            if link_elem:
                result.extra.setdefault("search_results", []).append({
                    "title": title_elem.get_text(strip=True) if title_elem else "",
                    "url": link_elem.get("href", ""),
                    "snippet": snippet_elem.get_text(strip=True) if snippet_elem else ""
                })
        
        return result
    
    def _extract_baike(self, url: str, html: str, result: ExtractionResult) -> ExtractionResult:
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'html.parser')
        
        title_elem = soup.select_one("#firstHeading, .lemmaTitle")
        result.title = title_elem.get_text(strip=True) if title_elem else ""
        
        content_elem = soup.select_one("#content, .lemma-content")
        if content_elem:
            result.content = content_elem.get_text(separator="\n", strip=True)
        
        toc = soup.select_one("#toc")
        if toc:
            result.extra["toc"] = toc.get_text(strip=True)
        
        refs = soup.select(".references li")
        result.extra["references"] = [r.get_text(strip=True) for r in refs]
        
        return result
    
    def _extract_zhidao(self, url: str, html: str, result: ExtractionResult) -> ExtractionResult:
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'html.parser')
        
        title_elem = soup.select_one(".ask-title, #question-title")
        result.title = title_elem.get_text(strip=True) if title_elem else ""
        
        best_answer = soup.select_one(".best-answer, .answer-text")
        if best_answer:
            result.content = best_answer.get_text(separator="\n", strip=True)
        
        return result
```

#### 2.5.3 搜狐提取器 (SohuExtractor)

```python
class SohuExtractor(BaseExtractor):
    """搜狐新闻/文章提取器"""
    
    NEEDS_JAVASCRIPT = False
    DOMAIN_PATTERNS = ["sohu.com"]
    
    def extract(self, url: str, html: str) -> ExtractionResult:
        from bs4 import BeautifulSoup
        
        result = ExtractionResult(url=url, extractor=self.get_extractor_name())
        soup = BeautifulSoup(html, 'html.parser')
        
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        
        title = soup.find("meta", property="og:title")
        if title:
            result.title = title.get("content", "")
        else:
            h1 = soup.find("h1")
            result.title = h1.get_text(strip=True) if h1 else ""
        
        article = soup.find("article")
        if not article:
            article = soup.find(class_=lambda x: x and "article" in x.lower())
        
        if article:
            result.content = article.get_text(separator="\n", strip=True)
        
        for img in soup.select(".article-content img, article img"):
            src = img.get("src") or img.get("data-src")
            if src:
                result.images.append({"url": src, "alt": img.get("alt", "")})
        
        meta = {}
        desc = soup.find("meta", attrs={"name": "description"})
        if desc:
            meta["description"] = desc.get("content", "")
        
        author = soup.find("meta", attrs={"name": "author"})
        if author:
            meta["author"] = author.get("content", "")
        
        result.meta = meta
        
        return result
```

#### 2.5.4 夸克提取器 (QuarkExtractor)

```python
class QuarkExtractor(BaseExtractor):
    """夸克搜索提取器"""
    
    NEEDS_JAVASCRIPT = True  # 暂定需 Playwright, 需验证
    DOMAIN_PATTERNS = ["quark.so.com", "quark.cn"]
    
    def extract(self, url: str, html: str) -> ExtractionResult:
        from bs4 import BeautifulSoup
        
        result = ExtractionResult(url=url, extractor=self.get_extractor_name())
        soup = BeautifulSoup(html, 'html.parser')
        
        title = soup.find("title")
        result.title = title.get_text(strip=True) if title else ""
        
        for item in soup.select(".result, .search-result, .item"):
            title_elem = item.select_one("title, h3, .title")
            link_elem = item.select_one("a")
            
            if link_elem:
                result.extra.setdefault("search_results", []).append({
                    "title": title_elem.get_text(strip=True) if title_elem else "",
                    "url": link_elem.get("href", "")
                })
        
        return result
```

#### 2.5.5 Wiki 提取器 (WikiExtractor)

```python
class WikiExtractor(BaseExtractor):
    """通用百科/Wiki 提取器"""
    
    NEEDS_JAVASCRIPT = False
    DOMAIN_PATTERNS = [
        "wikipedia.org",
        "baike.baidu.com",
        "zhihu.com", 
        "wikihow.com"
    ]
    
    def pre_validate(self, url: str, html: str) -> bool:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        
        if "wikipedia.org" in parsed.netloc:
            self._wiki_type = "wikipedia"
        elif "baike.baidu.com" in parsed.netloc:
            self._wiki_type = "baidu_baike"
        elif "zhihu.com" in parsed.netloc:
            self._wiki_type = "zhihu"
        elif "wikihow.com" in parsed.netloc:
            self._wiki_type = "wikihow"
        else:
            self._wiki_type = "generic"
        
        return True
    
    def extract(self, url: str, html: str) -> ExtractionResult:
        from bs4 import BeautifulSoup
        
        result = ExtractionResult(url=url, extractor=self.get_extractor_name())
        soup = BeautifulSoup(html, 'html.parser')
        
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        
        if hasattr(self, '_wiki_type'):
            if self._wiki_type == "wikipedia":
                return self._extract_wikipedia(soup, result)
            elif self._wiki_type == "baidu_baike":
                return self._extract_baidu_baike(soup, result)
            elif self._wiki_type == "zhihu":
                return self._extract_zhihu(soup, result)
        
        return self._extract_generic(soup, result)
    
    def _extract_wikipedia(self, soup: BeautifulSoup, result: ExtractionResult) -> ExtractionResult:
        heading = soup.find(id="firstHeading")
        result.title = heading.get_text(strip=True) if heading else ""
        
        content = soup.find(id="mw-content-text")
        if content:
            result.content = content.get_text(separator="\n", strip=True)
        
        toc = soup.find(id="toc")
        if toc:
            result.extra["toc"] = toc.get_text(strip=True)
        
        refs = soup.select(".references li")
        result.extra["references"] = [r.get_text(strip=True) for r in refs[:10]]
        
        infobox = soup.find(class_="infobox")
        if infobox:
            result.extra["infobox"] = infobox.get_text(separator="\n", strip=True)
        
        return result
    
    def _extract_baidu_baike(self, soup: BeautifulSoup, result: ExtractionResult) -> ExtractionResult:
        title = soup.find(class_="lemmaTitle")
        result.title = title.get_text(strip=True) if title else ""
        
        content = soup.find(class_="lemma-content")
        if content:
            result.content = content.get_text(separator="\n", strip=True)
        
        return result
    
    def _extract_zhihu(self, soup: BeautifulSoup, result: ExtractionResult) -> ExtractionResult:
        title = soup.find("meta", property="og:title")
        result.title = title.get("content", "") if title else ""
        
        content = soup.find(class_="RichText")
        if content:
            result.content = content.get_text(separator="\n", strip=True)
        
        return result
    
    def _extract_generic(self, soup: BeautifulSoup, result: ExtractionResult) -> ExtractionResult:
        result.title = soup.title.get_text(strip=True) if soup.title else ""
        
        main = soup.find("main") or soup.find("article")
        if main:
            result.content = main.get_text(separator="\n", strip=True)
        
        return result
```

---

## 3. 数据存储规范设计

### 3.1 JSON 输出结构

```json
{
  "url": "https://example.com/article",
  "title": "文章标题",
  "content": "文章正文内容...",
  "images": [
    {
      "url": "https://example.com/img1.jpg",
      "alt": "图片描述",
      "type": "content"
    }
  ],
  "videos": [
    {
      "url": "https://example.com/video.mp4",
      "cover": "https://example.com/cover.jpg",
      "duration": 120,
      "format": "mp4"
    }
  ],
  "meta": {
    "description": "页面描述",
    "author": "作者名",
    "published_time": "2024-01-01T00:00:00Z"
  },
  "extra": {
    "site_specific_field": "值"
  },
  "extracted_at": "2024-01-01T12:00:00.000000",
  "extractor": "GeneralExtractor"
}
```

#### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `url` | string | 是 | 原始 URL |
| `title` | string | 是 | 页面标题 |
| `content` | string | 否 | 主内容文本 |
| `images` | array | 否 | 图片列表 |
| `videos` | array | 否 | 视频列表 |
| `meta` | object | 否 | 元信息 |
| `extra` | object | 否 | 站点特定扩展数据 |
| `extracted_at` | string | 是 | 提取时间 (ISO8601) |
| `extractor` | string | 是 | 使用的提取器名称 |

### 3.2 Markdown 输出模板

```markdown
# {title}

**来源**: {url}

**提取时间**: {extracted_at}

**提取器**: {extractor}

---

## 摘要

{meta.description}

---

## 正文

{content}

---

## 图片

{images_list}

---

## 视频

{videos_list}

---

## 元信息

- **作者**: {meta.author}
- **发布时间**: {meta.published_time}

---

## 站点特定信息

{extra_fields}
```

### 3.3 文件命名规则

采用 **`{domain}_{timestamp}_{hash6}.{ext}`** 格式：

- `domain`: 域名 (不含 www., 如 `bilibili`)
- `timestamp`: `YYYYMMDD_HHMMSS`
- `hash6`: URL 哈希前 6 位 (防重复)

**示例**:
```
bilibili_bv123456_20240315_143022_a1b2c3.json
douyin_20240315_144530_d4e5f6.md
baike_20240315_145100_g7h8i9.json
```

### 3.4 目录结构

```
~/Downloads/crawler/output/
├── 2024/
│   ├── 03/
│   │   ├── 15/
│   │   │   ├── bilibili_bv123456_20240315_143022_a1b2c3.json
│   │   │   ├── bilibili_bv123456_20240315_143022_a1b2c3.md
│   │   │   ├── douyin_20240315_144530_d4e5f6.json
│   │   │   └── baike_20240315_145100_g7h8i9.json
│   │   └── ...
│   └── ...
└── latest/                    # 最新下载的软链接
    ├── bilibili.json -> ../2024/03/15/bilibili_xxx.json
    └── douyin.json -> ../2024/03/15/douyin_xxx.json
```

**设计说明**:
- 按 **年/月/日** 层级: 避免单目录文件过多
- `latest/` 目录: 软链接指向最新下载, 便于快速访问
- 可选: 支持 `--output` 参数覆盖默认目录

---

## 4. 测试矩阵

### 4.1 测试用例表

| 场景 | URL 示例 | 预期提取器 | Playwright | 验证点 |
|------|----------|-----------|------------|--------|
| B站视频 | `https://www.bilibili.com/video/BV1xx411c7mD` | BilibiliExtractor | 需 | title, videos, images |
| 抖音视频 | `https://v.douyin.com/xxx` | DouyinExtractor | 需 | title, videos, author |
| 百度搜索 | `https://www.baidu.com/s?wd=test` | BaiduExtractor | 否 | search_results |
| 百度百科 | `https://baike.baidu.com/item/Python` | BaiduExtractor | 否 | title, content, references |
| 搜狐新闻 | `https://www.sohu.com/a/xxx` | SohuExtractor | 否 | title, content, images |
| 夸克搜索 | `https://quark.so.com/s?wd=test` | QuarkExtractor | 需 | title, search_results |
| Wikipedia | `https://en.wikipedia.org/wiki/Python` | WikiExtractor | 否 | title, content, toc |
| 百度百科 | `https://baike.baidu.com/item/Python` | WikiExtractor | 否 | title, content |
| 知乎文章 | `https://zhuanlan.zhihu.com/p/xxx` | WikiExtractor | 否 | title, content |
| 通用页面 | `https://example.com` | GeneralExtractor | 否 | title, content |

### 4.2 边界条件测试

| 条件 | 测试用例 | 预期行为 |
|------|----------|----------|
| 空 HTML | HTML 为空字符串 | 返回含 url, title="" 的结果 |
| 无效 URL | `not-a-url` | 抛出异常或返回错误 |
| 404 页面 | 任意 404 URL | 返回错误信息 |
| 超大页面 | HTML > 10MB | 超时或截断处理 |
| 特殊字符标题 | 标题含 `<>&"` 等 | 正确转义 |
| 无内容页面 | 纯 JS 渲染无 HTML | 降级到 Playwright |
| 重定向 | URL 301/302 跳转 | 处理跳转后的内容 |
| 二进制内容 | 图片/文件 URL | 返回原始数据或跳过 |

### 4.3 Playwright 降级策略

```python
# src/crawler.py - 增强的降级逻辑

class Crawler:
    def crawl(self, url: str) -> Dict:
        # 第一步: 尝试 requests
        html = self._fetch(url)
        
        # 第二步: 判断是否需要 Playwright
        if self._should_use_playwright(url):
            html = self._fetch_with_playwright(url)
        
        # 第三步: 如果内容为空或检测到 JS 占位符, 降级到 Playwright
        if self._needs_javascript_fallback(html):
            if not self.use_playwright:
                print(f"Warning: Falling back to Playwright for {url}")
            html = self._fetch_with_playwright(url)
        
        # 第四步: 提取内容
        extractor = get_extractor(url)
        content = extractor.extract(url, html or "")
        
        return content
    
    def _needs_javascript_fallback(self, html: str) -> bool:
        """检测是否需要 JS 渲染降级"""
        if not html:
            return True
        
        fallback_indicators = [
            "JavaScript is required",
            "Enable JavaScript",
            "window.__INITIAL_STATE__",
            # 抖音特定
            "请在客户端打开",
        ]
        
        return any(indicator in html for indicator in fallback_indicators)
```

### 4.4 回归测试检查清单

```bash
# tests/test_extractors_regression.sh

# 1. 验证旧接口兼容
python -c "
from src.extractors import get_extractor
ext = get_extractor('https://www.bilibili.com/video/BV123')
print(type(ext).__name__)  # 应输出 BilibiliExtractor

ext = get_extractor('https://example.com')
print(type(ext).__name__)  # 应输出 GeneralExtractor
"

# 2. 验证新增提取器
python -c "
from src.extractors import get_extractor
ext = get_extractor('https://v.douyin.com/abc')
print(type(ext).__name__)  # 应输出 DouyinExtractor
"

# 3. 验证 JSON 输出结构
python -c "
from src.crawler import crawl
result = crawl('https://example.com', formats=['json'])
import json
data = json.load(open(result['exports']['json']))
assert 'url' in data
assert 'title' in data
assert 'extracted_at' in data
assert 'extractor' in data
print('JSON structure OK')
"
```

---

## 5. 验收标准

### 5.1 必须通过

| 验收项 | 标准 |
|--------|------|
| 旧接口兼容 | `get_extractor(url)` 对现有调用方透明 |
| B站提取 | 现有 `BilibiliExtractor` 逻辑完整迁移 |
| 新增抖音 | 抖音 URL 正确路由到 `DouyinExtractor` |
| 新增百度 | 百度搜索/百科正确路由到 `BaiduExtractor` |
| 新增搜狐 | 搜狐文章正确路由到 `SohuExtractor` |
| 新增夸克 | 夸克搜索正确路由到 `QuarkExtractor` |
| 新增 Wiki | Wikipedia/百度百科/知乎正确路由到 `WikiExtractor` |
| JSON 输出 | 符合 3.1 节定义的 JSON 结构 |
| Markdown 输出 | 符合 3.2 节的模板格式 |
| 文件命名 | 符合 3.3 节的命名规则 |
| 目录结构 | 符合 3.4 节的目录层级 |
| 测试覆盖 | 4.1 节测试用例全部通过 |

### 5.2 可降级项

| 验收项 | 降级条件 |
|--------|----------|
| 夸克 Playwright | 如验证无需 JS，可降级为 `NEEDS_JAVASCRIPT=False` |
| 搜狐图片提取 | 如页面结构变化，可简化提取逻辑 |
| 百度搜索结果 | 如 AJAX 加载，可降级到 Playwright |

---

## 6. 实施建议

### 实施顺序

1. **阶段一**: 架构重构 (base.py, registry.py, 目录拆分)
2. **阶段二**: 迁移现有提取器 (BilibiliExtractor, GeneralExtractor, GitHubExtractor, ImageExtractor)
3. **阶段三**: 实现抖音提取器 (优先级最高)
4. **阶段四**: 实现百度/百科提取器
5. **阶段五**: 实现搜狐/夸克/Wiki 提取器
6. **阶段六**: 完善测试与边界处理

### 风险提示

| 风险项 | 影响 | 缓解措施 |
|--------|------|----------|
| 抖音反爬 | 提取失败 | 使用 Playwright + 代理 |
| 百度结果 AJAX | 提取不完整 | 默认启用 Playwright |
| 页面结构变更 | 提取失败 | 预留 pre_validate 机制 |
| 性能瓶颈 | 多 JS 站点并发慢 | 考虑异步机制 |

---

## 附录: 变更影响面

### 需要改动的文件

| 文件 | 改动类型 | 风险 |
|------|----------|------|
| `src/extractors.py` | 重构拆分 | 高 (需完整迁移) |
| `src/extractors/__init__.py` | 新增 | 低 |
| `src/extractors/base.py` | 新增 | 低 |
| `src/extractors/registry.py` | 新增 | 低 |
| `src/extractors/douyin.py` | 新增 | 中 |
| `src/extractors/baidu.py` | 新增 | 中 |
| `src/extractors/sohu.py` | 新增 | 低 |
| `src/extractors/quark.py` | 新增 | 中 |
| `src/extractors/wiki.py` | 新增 | 中 |
| `src/exporters.py` | 增强 | 低 (文件命名规则) |
| `src/config.py` | 增强 | 低 (可选配置) |

### 不需要改动的文件

- `main.py` (CLI 入口保持不变)
- 现有测试文件 (除非新增测试用例)

---

*方案完成 - 等待 calamitas 评审*