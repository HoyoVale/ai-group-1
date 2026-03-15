# 通用爬虫工具完善 - 侦察报告

## 任务信息
- **任务ID**: crawler-enhancement
- **仓库路径**: `/home/hoyo/ai-group-1/projects/crawler/`
- **任务类型**: 架构分析与实现建议

---

## 1. 现有架构分析

### 1.1 核心文件结构

```
crawler/
├── main.py                 # CLI 入口
├── src/
│   ├── crawler.py          # 主爬虫逻辑 (核心调度)
│   ├── extractors.py       # 内容提取器 (关键模块)
│   ├── exporters.py        # 输出格式处理
│   └── config.py           # 配置
├── tests/
└── README.md
```

### 1.2 现有提取器注册机制

**位置**: `src/extractors.py` → `get_extractor()` 函数

```python
def get_extractor(url: str) -> BaseExtractor:
    parsed = urlparse(url)
    hostname = parsed.netloc.lower()
    
    if "github.com" in hostname or "githubusercontent.com" in hostname:
        return GitHubExtractor()
    elif "bilibili.com" in hostname:
        return BilibiliExtractor()
    elif any(site in hostname for site in ["unsplash.com", "pexels.com", ...]):
        return ImageExtractor()
    else:
        return GeneralExtractor()
```

**特点**: 基于域名的简单字符串匹配，无优先级机制

### 1.3 Playwright 集成方式

**位置**: `src/crawler.py`

| 方法 | 功能 |
|------|------|
| `_init_playwright()` | 初始化 Chromium 浏览器，支持代理配置 |
| `_fetch_with_playwright(url)` | 获取 JS 渲染后的页面 |
| `_should_use_playwright(url)` | 静态判断：是否需要 JS 渲染 |
| `_needs_javascript(html)` | 动态判断：HTML 是否显示需要 JS |

**动态站点硬编码列表**:
```python
dynamic_domains = [
    "bilibili.com", "douyin.com", "weibo.com",
    "twitter.com", "x.com", "facebook.com",
    "instagram.com", "reddit.com",
    "taobao.com", "jd.com", "tmall.com"
]
```

### 1.4 输出格式处理

**位置**: `src/exporters.py`

| Exporter | 格式 | 状态 |
|----------|------|------|
| `JSONExporter` | JSON | ✅ 完整 |
| `CSVExporter` | CSV | ✅ 完整 (嵌套数据展平) |
| `MarkdownExporter` | MD | ✅ 完整 |
| `PDFFxporter` | PDF | ⚠️ 依赖 weasyprint |
| `ImageExporter` | 图片下载 | ✅ 完整 (含 Referer 反防盗链) |

---

## 2. 需求覆盖度分析

### 2.1 视频网站

| 网站 | 需求 | 现有实现 | 状态 |
|------|------|----------|------|
| B站 | 视频提取 | `BilibiliExtractor` | ✅ 已实现 |
| 抖音 | 视频提取 | ❌ 无 | 需新增 |

### 2.2 搜索网站

| 网站 | 需求 | 现有实现 | 状态 |
|------|------|----------|------|
| 百度 | 搜索结果提取 | ❌ 无 | 需新增 |
| 搜狐 | 搜索结果提取 | ❌ 无 | 需新增 |
| 夸克 | 搜索结果提取 | ❌ 无 | 需新增 |
| Wiki | 百科内容提取 | ❌ 无 | 需新增 |

### 2.3 通用网页

| 需求 | 现有实现 | 状态 |
|------|----------|------|
| 通用内容提取 | `GeneralExtractor` | ✅ 已实现 |

---

## 3. 需要新增的模块

### 3.1 提取器模块 (新增)

```
src/extractors/
├── __init__.py           # 导出 get_extractor
├── base.py               # BaseExtractor 基类
├── general.py            # GeneralExtractor (保留)
├── bilibili.py           # BilibiliExtractor (移动)
├── douyin.py             # ⭐ 新增
├── baidu.py              # ⭐ 新增
├── sohu.py               # ⭐ 新增
├── quark.py              # ⭐ 新增
├── wiki.py               # ⭐ 新增
└── image.py              # ImageExtractor (移动)
```

### 3.2 网站适配器接口设计

```python
# src/extractors/base.py
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

class BaseExtractor(ABC):
    """网站内容提取器基类"""
    
    # 需要 Playwright 的网站设为 True
    NEEDS_JAVASCRIPT: bool = False
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
    
    @abstractmethod
    def extract(self, url: str, html: str) -> Dict[str, Any]:
        """
        提取页面内容
        
        Args:
            url: 页面 URL
            html: HTML 内容
            
        Returns:
            Dict 包含:
                - url: 原始 URL
                - title: 标题
                - content: 主内容 (可选)
                - images: 图片列表 (可选)
                - videos: 视频列表 (可选)
                - meta: 元信息 (可选)
                - **其他站点特定字段
        """
        pass
    
    def pre_validate(self, url: str, html: str) -> bool:
        """
        可选：验证是否是正确的页面
        用于域名匹配后的二次确认
        """
        return True
```

### 3.3 注册机制增强

```python
# src/extractors/registry.py
from typing import Dict, Type, Callable

class ExtractorRegistry:
    """提取器注册中心"""
    
    def __init__(self):
        # 匹配规则: (域名模式, 优先级, 提取器类)
        self._rules: List[tuple] = []
    
    def register(self, domain_pattern: str, priority: int = 0):
        """装饰器注册"""
        def decorator(cls: Type[BaseExtractor]):
            self._rules.append((domain_pattern, priority, cls))
            # 按优先级排序
            self._rules.sort(key=lambda x: x[1], reverse=True)
            return cls
        return decorator
    
    def get_extractor(self, url: str) -> BaseExtractor:
        for pattern, _, cls in self._rules:
            if pattern in url:
                return cls()
        return GeneralExtractor()

# 使用示例
registry = ExtractorRegistry()

@registry.register("douyin.com", priority=10)
class DouyinExtractor(BaseExtractor):
    NEEDS_JAVASCRIPT = True
    ...

@registry.register("baidu.com", priority=10)
class BaiduExtractor(BaseExtractor):
    ...
```

---

## 4. 各网站适配器设计建议

### 4.1 抖音 (Douyin)

```python
class DouyinExtractor(BaseExtractor):
    NEEDS_JAVASCRIPT = True  # 必须使用 Playwright
    
    def extract(self, url: str, html: str) -> Dict:
        # 提取点:
        # - 视频标题: <title>, og:title
        # - 视频链接: window.__INITIAL_STATE__.itemInfo.itemStruct.video
        # - 封面图: og:image
        # - 作者信息: window.__INITIAL_STATE__.itemInfo.itemStruct.author
        # - 点赞/评论数
```

**关键点**:
- 必须使用 Playwright (douyin.com 完全动态渲染)
- 视频 URL 需从 JSON 数据中提取 `playAddr`
- 需处理短链 `https://v.douyin.com/xxx`

### 4.2 百度 (Baidu)

```python
class BaiduExtractor(BaseExtractor):
    NEEDS_JAVASCRIPT = False  # 搜索结果页静态可读
    
    def extract(self, url: str, html: str) -> Dict:
        # 提取点:
        # - 搜索结果: .result, .c-container
        # - 百度百科: baike.baidu.com → 词条内容
        # - 百度知道: zhidao.baidu.com → 问答
```

**关键点**:
- 通用搜索结果静态可提取
- 需区分 `baidu.com/s` (搜索) 和 `baike.baidu.com` (百科)
- 百科内容可复用 GeneralExtractor 并增强

### 4.3 搜狐 (Sohu)

```python
class SohuExtractor(BaseExtractor):
    NEEDS_JAVASCRIPT = False
    
    def extract(self, url: str, html: str) -> Dict:
        # 提取点:
        # - 标题: <title>, h1
        # - 正文: .article-content, .text
        # - 图片: .img
```

**关键点**:
- 主要为新闻/文章类网站
- 静态 HTML 即可提取

### 4.4 夸克 (Quark)

```python
class QuarkExtractor(BaseExtractor):
    NEEDS_JAVASCRIPT = True  # 可能需要
    
    def extract(self, url: str, html: str) -> Dict:
        # 提取点:
        # - 搜索结果
        # - 网盘内容 (如涉及)
```

**关键点**:
- 夸克搜索 (quark.so.com)
- 需验证是否需要 JS 渲染

### 4.5 Wiki 类网站

```python
class WikiExtractor(BaseExtractor):
    """通用百科/ Wiki 提取器"""
    
    # 支持的 Wiki 站点
    WIKI_DOMAINS = [
        "wikipedia.org",
        "baike.baidu.com", 
        "zhihu.com",
        "wikihow.com"
    ]
    
    NEEDS_JAVASCRIPT = False
    
    def extract(self, url: str, html: str) -> Dict:
        # 提取点:
        # - 词条标题: #firstHeading
        # - 正文: #mw-content-text
        # - 目录: #toc
        # - 参考资料: .references
```

---

## 5. 实现思路

### 5.1 第一阶段：架构重构

1. **拆分 extractors.py**
   - 创建 `src/extractors/` 目录
   - 各提取器独立文件
   - 新增 `registry.py` 替换原 `get_extractor()`

2. **增强配置**
   - 可配置的动态域名列表 (从 config.py 读取)
   - 提取器优先级配置

### 5.2 第二阶段：新增提取器

优先级排序:
1. **高优先**: 抖音 (需求明确，必须 Playwright)
2. **中优先**: 百度、百科类 (搜索场景常用)
3. **低优先**: 搜狐、夸克 (视需求)

### 5.3 测试策略

```python
# tests/test_extractors.py
def test_bilibili_extractor():
    # 测试 B 站视频提取
    
def test_douyin_extractor():
    # 测试抖音提取 (需要 mock Playwright)
    
def test_registry_fallback():
    # 测试未知域名回退到 GeneralExtractor
```

---

## 6. 潜在风险

| 风险项 | 说明 | 缓解措施 |
|--------|------|----------|
| 抖音反爬 | 抖音有较强反爬机制 | 使用 Playwright + 代理 |
| 搜索结果动态加载 | 百度结果可能 AJAX 加载 | 默认启用 Playwright |
| 页面结构变更 | 网站改版导致提取失败 | 预留 pre_validate 机制 |
| 性能 | 多 JS 站点并发慢 | 考虑异步/并发机制 |

---

## 7. 总结

现有爬虫架构清晰，提取器采用简单的域名匹配 + 继承基类模式。需完善:

1. **抖音提取器** - 必须新增，需 Playwright
2. **搜索/百科提取器** - 百度、Wiki 等通用场景
3. **注册机制增强** - 支持优先级和配置化

**建议实施顺序**: 抖音 → 百度/百科 → 其他

---

*报告生成时间: 2026-03-15*
*侦察员: Calamitas*
