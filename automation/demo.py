#!/usr/bin/env python3
"""
AgentBus Browser Automation Demo

演示浏览器自动化系统的基本功能
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from agentbus.automation import BrowserAutomation, BrowserConfig


async def demo_basic_navigation():
    """演示基本导航功能"""
    print("🌐 基本导航演示...")
    
    config = BrowserConfig(headless=False, timeout=10000)
    
    async with BrowserAutomation(config) as browser:
        try:
            # 访问百度
            print("正在访问百度...")
            await browser.navigate_to("https://www.baidu.com")
            
            # 截图
            screenshot_path = await browser.take_screenshot(
                path="./demo_baidu_homepage.png",
                full_page=False
            )
            print(f"✅ 首页截图已保存: {screenshot_path}")
            
            # 获取页面信息
            page_info = await browser.get_page_info()
            print(f"📄 页面标题: {page_info.get('title', 'Unknown')}")
            print(f"🔗 当前URL: {page_info.get('url', 'Unknown')[:50]}...")
            
            # 搜索
            print("正在执行搜索...")
            await browser.type_text(
                selector="input[name='wd']",
                value="AgentBus 浏览器自动化"
            )
            
            await browser.click_element(
                selector="input[type='submit']"
            )
            
            # 等待结果加载
            await browser.page_navigator.wait_for_load_state("networkidle")
            
            # 截图搜索结果
            search_screenshot = await browser.take_screenshot(
                path="./demo_search_results.png",
                full_page=True
            )
            print(f"✅ 搜索结果截图已保存: {search_screenshot}")
            
        except Exception as e:
            print(f"❌ 演示过程中出错: {e}")


async def demo_form_automation():
    """演示表单自动化"""
    print("\n📝 表单自动化演示...")
    
    config = BrowserConfig(headless=False, timeout=10000)
    
    # 创建测试表单页面
    test_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>演示表单</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f0f0f0; }
            .form-container { 
                background: white; 
                padding: 30px; 
                border-radius: 10px; 
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                max-width: 500px;
            }
            .form-group { margin-bottom: 20px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input, select { 
                width: 100%; 
                padding: 10px; 
                border: 1px solid #ddd; 
                border-radius: 5px;
                box-sizing: border-box;
            }
            .checkbox-group { margin: 10px 0; }
            button { 
                background: #007bff; 
                color: white; 
                padding: 12px 30px; 
                border: none; 
                border-radius: 5px; 
                cursor: pointer;
                margin-right: 10px;
            }
            button:hover { background: #0056b3; }
            .result { 
                margin-top: 20px; 
                padding: 15px; 
                background: #d4edda; 
                border: 1px solid #c3e6cb; 
                border-radius: 5px;
                display: none;
            }
        </style>
    </head>
    <body>
        <div class="form-container">
            <h1>用户注册演示</h1>
            <form id="demoForm">
                <div class="form-group">
                    <label for="username">用户名:</label>
                    <input type="text" id="username" name="username" required>
                </div>
                
                <div class="form-group">
                    <label for="email">邮箱地址:</label>
                    <input type="email" id="email" name="email" required>
                </div>
                
                <div class="form-group">
                    <label for="password">密码:</label>
                    <input type="password" id="password" name="password" required>
                </div>
                
                <div class="form-group">
                    <label for="country">国家/地区:</label>
                    <select id="country" name="country">
                        <option value="cn">中国</option>
                        <option value="us">美国</option>
                        <option value="jp">日本</option>
                        <option value="kr">韩国</option>
                    </select>
                </div>
                
                <div class="checkbox-group">
                    <label>
                        <input type="checkbox" id="newsletter" name="newsletter">
                        订阅我们的新闻邮件
                    </label>
                </div>
                
                <div class="checkbox-group">
                    <label>
                        <input type="checkbox" id="terms" name="terms" required>
                        我同意服务条款和隐私政策
                    </label>
                </div>
                
                <button type="submit">注册</button>
                <button type="reset">重置</button>
            </form>
            
            <div class="result" id="result">
                <h3>表单提交成功!</h3>
                <p id="resultContent"></p>
            </div>
        </div>
        
        <script>
            document.getElementById('demoForm').addEventListener('submit', function(e) {
                e.preventDefault();
                
                const formData = new FormData(this);
                const data = {};
                for (let [key, value] of formData.entries()) {
                    data[key] = value;
                }
                
                document.getElementById('resultContent').innerHTML = `
                    <strong>提交的数据:</strong><br>
                    用户名: ${data.username}<br>
                    邮箱: ${data.email}<br>
                    国家: ${data.country}<br>
                    订阅邮件: ${data.newsletter ? '是' : '否'}<br>
                    同意条款: ${data.terms ? '是' : '否'}
                `;
                
                document.getElementById('result').style.display = 'block';
            });
            
            document.getElementById('demoForm').addEventListener('reset', function() {
                document.getElementById('result').style.display = 'none';
            });
        </script>
    </body>
    </html>
    """
    
    async with BrowserAutomation(config) as browser:
        try:
            # 打开测试页面
            await browser.navigate_to(f"data:text/html,{test_html}")
            
            # 截图空白表单
            await browser.take_screenshot(
                path="./demo_form_before.png",
                full_page=False
            )
            
            # 填写表单数据
            form_data = {
                "input[name='username']": "demo_user_2024",
                "input[name='email']": "demo@example.com", 
                "input[name='password']": "SecurePass123",
                "select[name='country']": "cn",
                "input[name='newsletter']": True,
                "input[name='terms']": True
            }
            
            print("正在填写表单...")
            await browser.fill_form(form_data)
            
            # 截图填写后的表单
            await browser.take_screenshot(
                path="./demo_form_filled.png", 
                full_page=False
            )
            
            # 提交表单
            print("正在提交表单...")
            await browser.form_handler.submit_form("button[type='submit']")
            
            # 等待提交结果
            await asyncio.sleep(2)
            
            # 截图提交结果
            await browser.take_screenshot(
                path="./demo_form_result.png",
                full_page=False
            )
            
            print("✅ 表单自动化演示完成")
            
        except Exception as e:
            print(f"❌ 表单演示过程中出错: {e}")


async def demo_element_interaction():
    """演示元素交互功能"""
    print("\n🎯 元素交互演示...")
    
    config = BrowserConfig(headless=False, timeout=10000)
    
    test_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>元素交互演示</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #e3f2fd; }
            .container { max-width: 800px; margin: 0 auto; }
            .demo-section { 
                background: white; 
                padding: 20px; 
                margin: 20px 0; 
                border-radius: 8px; 
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }
            .interactive-btn { 
                background: #4CAF50; 
                color: white; 
                padding: 10px 20px; 
                border: none; 
                border-radius: 5px; 
                cursor: pointer; 
                margin: 5px;
            }
            .interactive-btn:hover { background: #45a049; }
            .output { 
                margin-top: 15px; 
                padding: 10px; 
                background: #f9f9f9; 
                border-left: 4px solid #4CAF50;
                min-height: 20px;
            }
            input[type="text"] { 
                padding: 8px; 
                margin: 5px; 
                border: 1px solid #ddd; 
                border-radius: 4px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎯 AgentBus 元素交互演示</h1>
            
            <div class="demo-section">
                <h3>按钮交互</h3>
                <button class="interactive-btn" id="clickBtn" onclick="handleClick()">点击我!</button>
                <button class="interactive-btn" id="hoverBtn" onmouseover="handleHover()" onmouseout="clearOutput()">悬停我!</button>
                <button class="interactive-btn" id="doubleClickBtn" ondblclick="handleDoubleClick()">双击我!</button>
                <div class="output" id="buttonOutput"></div>
            </div>
            
            <div class="demo-section">
                <h3>文本输入</h3>
                <input type="text" id="textInput" placeholder="在这里输入文字...">
                <button class="interactive-btn" onclick="clearText()">清除</button>
                <div class="output" id="textOutput"></div>
            </div>
            
            <div class="demo-section">
                <h3>动态内容</h3>
                <button class="interactive-btn" onclick="loadDynamicContent()">加载动态内容</button>
                <div class="output" id="dynamicOutput"></div>
            </div>
        </div>
        
        <script>
            let clickCount = 0;
            
            function handleClick() {
                clickCount++;
                document.getElementById('buttonOutput').innerHTML = 
                    `按钮被点击了 ${clickCount} 次! 🎉`;
            }
            
            function handleHover() {
                document.getElementById('buttonOutput').innerHTML = 
                    '鼠标悬停检测成功! 🖱️';
            }
            
            function handleDoubleClick() {
                document.getElementById('buttonOutput').innerHTML = 
                    '双击检测成功! ⚡';
            }
            
            function clearOutput() {
                setTimeout(() => {
                    document.getElementById('buttonOutput').innerHTML = '';
                }, 1000);
            }
            
            document.getElementById('textInput').addEventListener('input', function(e) {
                const value = e.target.value;
                document.getElementById('textOutput').innerHTML = 
                    value ? `输入的内容: "${value}" (${value.length} 个字符)` : '';
            });
            
            function clearText() {
                document.getElementById('textInput').value = '';
                document.getElementById('textOutput').innerHTML = '';
            }
            
            function loadDynamicContent() {
                const output = document.getElementById('dynamicOutput');
                output.innerHTML = '正在加载...';
                
                setTimeout(() => {
                    output.innerHTML = `
                        <h4>🚀 动态加载的内容</h4>
                        <p>这是通过JavaScript动态生成的内容。</p>
                        <p>加载时间: ${new Date().toLocaleTimeString()}</p>
                        <button class="interactive-btn" onclick="this.parentElement.innerHTML=''">关闭</button>
                    `;
                }, 1500);
            }
            
            console.log('元素交互演示页面已加载');
        </script>
    </body>
    </html>
    """
    
    async with BrowserAutomation(config) as browser:
        try:
            # 打开演示页面
            await browser.navigate_to(f"data:text/html,{test_html}")
            
            # 截图初始页面
            await browser.take_screenshot(
                path="./demo_interaction_start.png",
                full_page=True
            )
            
            print("正在演示按钮点击...")
            await browser.click_element(selector="#clickBtn")
            await asyncio.sleep(1)
            
            print("正在演示文本输入...")
            await browser.type_text(
                selector="#textInput", 
                value="AgentBus 自动化测试"
            )
            await asyncio.sleep(1)
            
            print("正在演示双击...")
            await browser.double_click_element(selector="#doubleClickBtn")
            await asyncio.sleep(1)
            
            print("正在演示悬停...")
            await browser.hover_element(selector="#hoverBtn")
            await asyncio.sleep(2)
            
            print("正在演示动态内容加载...")
            await browser.click_element(selector="#loadDynamicContent")
            await asyncio.sleep(3)
            
            # 最终截图
            await browser.take_screenshot(
                path="./demo_interaction_end.png",
                full_page=True
            )
            
            print("✅ 元素交互演示完成")
            
        except Exception as e:
            print(f"❌ 元素交互演示过程中出错: {e}")


async def demo_batch_screenshots():
    """演示批量截图功能"""
    print("\n📸 批量截图演示...")
    
    config = BrowserConfig(headless=False, timeout=10000)
    
    # 演示网站列表
    demo_sites = [
        {
            "name": "百度",
            "url": "https://www.baidu.com",
            "selector": "input[name='wd']"
        },
        {
            "name": "GitHub", 
            "url": "https://github.com",
            "selector": "[name='q']"
        },
        {
            "name": "示例页面",
            "url": "data:text/html,<h1>这是一个演示页面</h1><p>用于展示批量截图功能</p>",
            "selector": "h1"
        }
    ]
    
    async with BrowserAutomation(config) as browser:
        for i, site in enumerate(demo_sites, 1):
            try:
                print(f"正在访问第 {i} 个网站: {site['name']}")
                
                # 导航到网站
                await browser.navigate_to(site['url'])
                await browser.page_navigator.wait_for_load_state("networkidle")
                
                # 截图
                screenshot_path = await browser.take_screenshot(
                    path=f"./demo_batch_{i}_{site['name']}.png",
                    full_page=True
                )
                
                # 获取页面信息
                page_info = await browser.get_page_info()
                title = page_info.get('title', 'Unknown')
                
                print(f"  ✅ 截图已保存: {screenshot_path}")
                print(f"  📄 页面标题: {title}")
                
                # 等待一下再访问下一个
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"  ❌ 处理 {site['name']} 时出错: {e}")
                continue
        
        print("✅ 批量截图演示完成")


async def main():
    """主演示函数"""
    print("🚀 AgentBus 浏览器自动化系统演示")
    print("=" * 60)
    
    try:
        # 演示各种功能
        await demo_basic_navigation()
        await demo_form_automation()
        await demo_element_interaction()
        await demo_batch_screenshots()
        
        print("\n" + "=" * 60)
        print("🎉 所有演示完成!")
        print("=" * 60)
        
        print("\n📋 演示总结:")
        print("1. ✅ 基本导航 - 展示了页面访问和截图功能")
        print("2. ✅ 表单自动化 - 展示了表单填写和提交流程")
        print("3. ✅ 元素交互 - 展示了各种元素操作")
        print("4. ✅ 批量截图 - 展示了批量处理能力")
        
        print("\n📁 生成的文件:")
        for file in Path(".").glob("demo_*.png"):
            print(f"  📸 {file}")
            
        print("\n💡 提示:")
        print("- 所有的截图文件都已保存到当前目录")
        print("- 可以查看这些文件来了解系统的功能")
        print("- 如需了解更多功能，请查看 README.md")
        
    except Exception as e:
        print(f"\n❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 确保当前目录存在
    Path(".").mkdir(exist_ok=True)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 演示被用户中断")
    except Exception as e:
        print(f"\n❌ 演示启动失败: {e}")
        print("\n请确保已安装所需依赖:")
        print("pip install playwright")
        print("playwright install chromium")