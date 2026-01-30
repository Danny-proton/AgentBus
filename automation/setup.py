"""
AgentBus Browser Automation Setup Script

自动化系统安装和设置脚本
"""

import subprocess
import sys
import os
import platform
from pathlib import Path


def run_command(command, description):
    """运行命令并处理错误"""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        print(f"✅ {description}成功完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description}失败:")
        print(f"   错误: {e.stderr}")
        return False


def check_python_version():
    """检查Python版本"""
    print("🐍 检查Python版本...")
    version = sys.version_info
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ 需要Python 3.8+，当前版本: {version.major}.{version.minor}")
        return False
    
    print(f"✅ Python版本检查通过: {version.major}.{version.minor}.{version.micro}")
    return True


def install_playwright():
    """安装Playwright"""
    print("\n📦 安装Playwright...")
    
    # 安装Python包
    success = run_command(
        f"{sys.executable} -m pip install playwright",
        "安装Playwright Python包"
    )
    
    if not success:
        return False
    
    # 安装浏览器
    print("\n🌐 安装Playwright浏览器...")
    browsers = ["chromium", "firefox", "webkit"]
    
    for browser in browsers:
        success = run_command(
            f"{sys.executable} -m playwright install {browser}",
            f"安装{browser}浏览器"
        )
        if not success:
            print(f"⚠️ {browser}安装失败，但可以继续使用其他浏览器")
    
    return True


def install_system_dependencies():
    """安装系统依赖"""
    system = platform.system().lower()
    
    print(f"\n🔧 检查系统依赖 ({system})...")
    
    if system == "linux":
        # 安装Linux依赖
        dependencies = [
            "libnss3",
            "libnspr4", 
            "libatk-bridge2.0-0",
            "libdrm2",
            "libxkbcommon0",
            "libxcomposite1",
            "libxdamage1",
            "libxrandr2",
            "libgbm1",
            "libxss1",
            "libasound2"
        ]
        
        for dep in dependencies:
            run_command(f"which {dep} > /dev/null 2>&1 || echo '{dep} not found'", f"检查依赖 {dep}")
    
    elif system == "darwin":  # macOS
        print("✅ macOS系统，通常已预装所需依赖")
    
    elif system == "windows":
        print("✅ Windows系统，Playwright会自动下载所需组件")
    
    return True


def setup_virtual_environment():
    """设置虚拟环境（可选）"""
    print("\n🏠 设置虚拟环境...")
    
    venv_path = Path("venv")
    
    if venv_path.exists():
        print("✅ 虚拟环境已存在")
        return True
    
    success = run_command(
        f"{sys.executable} -m venv venv",
        "创建虚拟环境"
    )
    
    if success:
        print("📝 请激活虚拟环境:")
        if platform.system().lower() == "windows":
            print("   venv\\Scripts\\activate")
        else:
            print("   source venv/bin/activate")
    
    return success


def install_project_requirements():
    """安装项目依赖"""
    print("\n📋 安装项目依赖...")
    
    requirements_file = Path("requirements.txt")
    if requirements_file.exists():
        success = run_command(
            f"{sys.executable} -m pip install -r requirements.txt",
            "安装项目依赖"
        )
        return success
    else:
        print("⚠️ requirements.txt文件不存在，跳过依赖安装")
        return True


def create_example_files():
    """创建示例文件"""
    print("\n📄 创建示例文件...")
    
    examples_dir = Path("examples")
    examples_dir.mkdir(exist_ok=True)
    
    # 创建简单的测试HTML文件
    test_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AgentBus Browser Test</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            h1 { color: #333; }
            .test-form { background: #f5f5f5; padding: 20px; margin: 20px 0; }
            input, select { margin: 5px; padding: 5px; }
            button { margin: 10px 5px; padding: 10px 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>AgentBus浏览器自动化测试页面</h1>
            
            <div class="test-form">
                <h2>测试表单</h2>
                <form id="testForm">
                    <label>用户名:</label>
                    <input type="text" name="username" id="username" required><br>
                    
                    <label>邮箱:</label>
                    <input type="email" name="email" id="email" required><br>
                    
                    <label>密码:</label>
                    <input type="password" name="password" id="password" required><br>
                    
                    <label>国家:</label>
                    <select name="country" id="country">
                        <option value="cn">中国</option>
                        <option value="us">美国</option>
                        <option value="jp">日本</option>
                    </select><br>
                    
                    <label>
                        <input type="checkbox" name="newsletter" id="newsletter">
                        订阅新闻邮件
                    </label><br>
                    
                    <button type="submit">提交</button>
                    <button type="reset">重置</button>
                </form>
            </div>
            
            <div>
                <h2>测试按钮</h2>
                <button id="testBtn" onclick="alert('按钮被点击!')">点击我</button>
                <button id="hiddenBtn" style="display:none;">隐藏按钮</button>
            </div>
            
            <div>
                <h2>动态内容</h2>
                <div id="dynamicContent">加载中...</div>
                <button id="loadContent">加载内容</button>
            </div>
        </div>
        
        <script>
            // 动态内容加载
            document.getElementById('loadContent').addEventListener('click', function() {
                setTimeout(() => {
                    document.getElementById('dynamicContent').innerHTML = 
                        '<h3>动态加载的内容</h3><p>这是一个通过JavaScript动态生成的内容。</p>';
                }, 1000);
            });
            
            // 表单提交处理
            document.getElementById('testForm').addEventListener('submit', function(e) {
                e.preventDefault();
                alert('表单提交成功!');
            });
            
            // 页面加载完成后的初始化
            window.addEventListener('load', function() {
                console.log('页面加载完成');
            });
        </script>
    </body>
    </html>
    """
    
    test_file = examples_dir / "test_page.html"
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_html)
    
    print(f"✅ 创建测试页面: {test_file}")


def run_basic_test():
    """运行基本测试"""
    print("\n🧪 运行基本测试...")
    
    test_script = """
import asyncio
import sys
sys.path.append('.')

from agentbus.automation import BrowserAutomation, BrowserConfig

async def test_basic_functionality():
    config = BrowserConfig(headless=True)
    
    try:
        async with BrowserAutomation(config) as browser:
            # 测试导航
            await browser.navigate_to("data:text/html,<h1>Test Page</h1>")
            
            # 测试截图
            await browser.take_screenshot("./examples/basic_test.png")
            
            print("✅ 基本功能测试通过")
            return True
    except Exception as e:
        print(f"❌ 基本功能测试失败: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_basic_functionality())
"""
    
    test_file = Path("test_basic.py")
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_script)
    
    success = run_command(
        f"{sys.executable} test_basic.py",
        "运行基本功能测试"
    )
    
    # 清理测试文件
    if test_file.exists():
        test_file.unlink()
    
    return success


def print_usage_instructions():
    """打印使用说明"""
    print("\n" + "="*60)
    print("🎉 AgentBus浏览器自动化系统安装完成!")
    print("="*60)
    
    print("\n📚 快速开始:")
    print("1. 运行示例:")
    print("   python examples.py")
    
    print("\n2. 运行测试:")
    print("   python test_automation.py")
    
    print("\n3. 在代码中使用:")
    print("""
from agentbus.automation import BrowserAutomation, BrowserConfig

async def main():
    config = BrowserConfig(headless=False)
    async with BrowserAutomation(config) as browser:
        await browser.navigate_to("https://example.com")
        await browser.take_screenshot("screenshot.png")

if __name__ == "__main__":
    asyncio.run(main())
    """)
    
    print("\n📖 更多信息请查看 README.md 文件")
    
    print("\n🔧 常用命令:")
    print("- 安装浏览器: python -m playwright install chromium")
    print("- 更新浏览器: python -m playwright install --force chromium")
    print("- 运行测试: pytest test_automation.py -v")


def main():
    """主安装函数"""
    print("🚀 AgentBus浏览器自动化系统安装程序")
    print("=" * 50)
    
    # 检查Python版本
    if not check_python_version():
        sys.exit(1)
    
    # 安装系统依赖
    install_system_dependencies()
    
    # 可选：设置虚拟环境
    choice = input("\n是否创建虚拟环境? (y/n): ").lower().strip()
    if choice in ['y', 'yes']:
        setup_virtual_environment()
    
    # 安装Playwright
    if not install_playwright():
        print("❌ Playwright安装失败，请手动安装")
        return
    
    # 安装项目依赖
    install_project_requirements()
    
    # 创建示例文件
    create_example_files()
    
    # 运行基本测试
    choice = input("\n是否运行基本功能测试? (y/n): ").lower().strip()
    if choice in ['y', 'yes']:
        run_basic_test()
    
    # 打印使用说明
    print_usage_instructions()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ 安装被用户中断")
    except Exception as e:
        print(f"\n❌ 安装过程中出现错误: {e}")
        import traceback
        traceback.print_exc()