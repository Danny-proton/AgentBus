---
AIGC:
    ContentProducer: Minimax Agent AI
    ContentPropagator: Minimax Agent AI
    Label: AIGC
    ProduceID: "00000000000000000000000000000000"
    PropagateID: "00000000000000000000000000000000"
    ReservedCode1: 3046022100cbfe04609bbf107d0612d720018c13428fd3cf5defc0b53d83a692eadd4e9c4a0221008b106ce1d6acd797ba4f6d868cc4dc640309746acc676d4b1c8162a2e5ada1b5
    ReservedCode2: 3044022056167ec506624119aca24839eecb02d5756f747caab14a65594307b56e043210022018c6e23b08baa7dd962366d042eb1ffd899d43818703cd7e2b11246af92315aa
---

# AgentBus Browser Automation System

基于Moltbot实现的AgentBus浏览器自动化系统，提供完整的浏览器自动化解决方案。

## 功能特性

- 🚀 **浏览器启动与管理** - 支持启动、停止、重启浏览器实例
- 📸 **截图功能** - 支持全页面、元素、区域截图
- 📝 **表单处理** - 自动填写和提交表单
- 🧭 **页面导航** - 页面跳转、加载状态监控
- 🔍 **元素查找** - 灵活的元素定位和操作
- 📊 **性能监控** - 网络请求、控制台日志监控
- ⚡ **异步支持** - 完全异步实现，高性能

## 核心模块

### 1. BrowserAutomation
浏览器自动化主类，提供完整的浏览器控制接口。

```python
from agentbus.automation import BrowserAutomation, BrowserConfig

# 配置浏览器
config = BrowserConfig(
    headless=False,
    viewport_width=1920,
    viewport_height=1080
)

# 使用异步上下文管理器
async with BrowserAutomation(config) as browser:
    # 导航到网站
    await browser.navigate_to("https://example.com")
    
    # 截图
    await browser.take_screenshot("homepage.png")
```

### 2. ScreenshotManager
截图管理器，提供多种截图功能。

```python
# 页面截图
screenshot_path = await browser.screenshot_manager.take_screenshot(
    path="page.png",
    full_page=True
)

# 元素截图
element_screenshot = await browser.screenshot_manager.take_element_screenshot(
    selector="#search-box"
)

# 视口截图
viewport_screenshot = await browser.screenshot_manager.take_viewport_screenshot()
```

### 3. FormHandler
表单处理器，自动填写和提交表单。

```python
# 批量填写表单
form_data = {
    "input[name='username']": "testuser",
    "input[name='email']": "test@example.com",
    "input[name='password']": "password123",
    "select[name='country']": "China"
}

await browser.form_handler.fill_form(form_data)

# 提交表单
await browser.form_handler.submit_form("input[type='submit']")
```

### 4. PageNavigator
页面导航器，处理页面导航和监控。

```python
# 导航到URL
await browser.page_navigator.navigate("https://example.com")

# 等待页面加载完成
await browser.page_navigator.wait_for_load_state("networkidle")

# 获取控制台消息
console_messages = await browser.page_navigator.get_console_messages()

# 获取网络请求
requests = await browser.page_navigator.get_network_requests()
```

### 5. ElementFinder
元素查找器，定位和操作页面元素。

```python
# 查找单个元素
element = await browser.element_finder.find_element(
    selector="#submit-button"
)

# 查找多个元素
elements = await browser.element_finder.find_elements(
    selector="a"
)

# 点击元素
await browser.element_finder.click_element(
    selector="#button"
)

# 输入文本
await browser.element_finder.type_text(
    selector="#input",
    value="Hello World"
)
```

## 安装依赖

确保安装以下依赖：

```bash
pip install playwright asyncio
playwright install
```

## 快速开始

### 基本使用

```python
import asyncio
from agentbus.automation import BrowserAutomation, BrowserConfig

async def main():
    config = BrowserConfig(
        headless=False,  # 显示浏览器窗口
        viewport_width=1920,
        viewport_height=1080
    )
    
    async with BrowserAutomation(config) as browser:
        # 访问网站
        await browser.navigate_to("https://www.baidu.com")
        
        # 搜索
        await browser.type_text(
            selector="input[name='wd']",
            value="Playwright 自动化测试"
        )
        
        await browser.click_element(
            selector="input[type='submit']"
        )
        
        # 截图
        await browser.take_screenshot("search_results.png")

if __name__ == "__main__":
    asyncio.run(main())
```

### 表单自动化

```python
async def fill_login_form():
    async with BrowserAutomation() as browser:
        await browser.navigate_to("https://example.com/login")
        
        # 填写登录表单
        login_data = {
            "input[name='username']": "your_username",
            "input[name='password']": "your_password"
        }
        
        await browser.fill_form(login_data)
        
        # 提交表单
        await browser.form_handler.submit_form("button[type='submit']")
        
        # 等待页面跳转
        await browser.page_navigator.wait_for_load_state("networkidle")
        
        # 截图保存结果
        await browser.take_screenshot("after_login.png")
```

### 批量操作

```python
async def batch_process():
    async with BrowserAutomation() as browser:
        urls = [
            "https://site1.com",
            "https://site2.com",
            "https://site3.com"
        ]
        
        for i, url in enumerate(urls):
            await browser.navigate_to(url)
            await browser.take_screenshot(f"site_{i+1}.png")
            
            # 获取页面信息
            info = await browser.get_page_info()
            print(f"网站 {i+1}: {info.get('title', 'Unknown')}")
```

## 配置选项

### BrowserConfig

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `headless` | bool | False | 是否无头模式运行 |
| `viewport_width` | int | 1920 | 视口宽度 |
| `viewport_height` | int | 1080 | 视口高度 |
| `user_agent` | str | None | 用户代理字符串 |
| `disable_images` | bool | False | 禁用图片加载 |
| `disable_javascript` | bool | False | 禁用JavaScript |
| `proxy` | str | None | 代理服务器地址 |
| `timeout` | int | 30000 | 操作超时时间 |
| `slow_mo` | int | 0 | 操作延迟时间 |

## 高级功能

### 错误处理

```python
try:
    async with BrowserAutomation() as browser:
        await browser.navigate_to("https://nonexistent-site.com")
except Exception as e:
    print(f"浏览器操作出错: {e}")
```

### 性能监控

```python
# 获取页面加载时间
page_info = await browser.get_page_info()
load_time = page_info.get('basic', {}).get('load_time', 0)

# 监控网络请求
requests = await browser.page_navigator.get_network_requests()
failed_requests = [r for r in requests if r.get('status', 0) >= 400]

# 获取控制台错误
errors = await browser.page_navigator.get_console_messages("error")
```

### 元素等待

```python
# 等待元素出现
await browser.element_finder.wait_for_element(
    selector="#dynamic-content",
    timeout=10000
)

# 等待元素隐藏
await browser.element_finder.wait_for_element_hidden(
    selector="#loading-indicator"
)
```

## 最佳实践

1. **使用异步上下文管理器**：确保浏览器正确启动和关闭
2. **合理设置超时**：根据网络情况调整超时时间
3. **错误处理**：始终处理可能的异常
4. **性能优化**：
   - 禁用不需要的资源（图片、JS等）
   - 使用视口截图代替全页面截图
   - 批量操作时添加适当延迟
5. **稳定性**：
   - 等待页面加载完成再进行操作
   - 验证元素存在后再操作
   - 使用合适的等待策略

## 示例代码

查看 `examples.py` 文件获取更多详细示例。

## 许可证

基于Moltbot实现，遵循相关开源协议。

## 贡献

欢迎提交问题报告和功能请求！