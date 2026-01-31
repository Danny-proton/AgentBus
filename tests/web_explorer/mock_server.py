"""
WebExplorer Agent Mock Server

基于 FastAPI 的轻量级测试服务器,用于 WebExplorer Agent 的测试。
提供多种页面类型用于测试不同的导航场景。

运行方式:
    python tests/web_explorer/mock_server.py

访问地址:
    http://127.0.0.1:8080
"""

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
import uvicorn

app = FastAPI(title="Mock Site for WebExplorer Testing")


@app.get("/", response_class=HTMLResponse)
async def home():
    """首页 - 包含导航到所有主要页面的链接"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Mock Site - Home</title>
        <meta charset="utf-8">
    </head>
    <body>
        <h1>Welcome to Mock Site</h1>
        <p>This is a test website for WebExplorer Agent.</p>
        <nav>
            <ul>
                <li><a href="/products" id="products-link">Products</a></li>
                <li><a href="/login" id="login-link">Login</a></li>
                <li><a href="/about" id="about-link">About</a></li>
                <li><a href="/deadend" id="deadend-link">Dead End</a></li>
                <li><a href="/loop-a" id="loop-link">Loop Test</a></li>
            </ul>
        </nav>
    </body>
    </html>
    """


@app.get("/products", response_class=HTMLResponse)
async def products():
    """产品列表页 - 显示3个产品"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Products</title>
        <meta charset="utf-8">
    </head>
    <body>
        <h1>Product List</h1>
        <p>Browse our amazing products:</p>
        <ul>
            <li><a href="/products/1" id="product-1">Product 1 - Laptop</a></li>
            <li><a href="/products/2" id="product-2">Product 2 - Mouse</a></li>
            <li><a href="/products/3" id="product-3">Product 3 - Keyboard</a></li>
        </ul>
        <a href="/" id="home-link">Back to Home</a>
    </body>
    </html>
    """


@app.get("/products/{product_id}", response_class=HTMLResponse)
async def product_detail(product_id: int):
    """产品详情页 - 第3层深度"""
    product_names = {
        1: "Laptop",
        2: "Mouse",
        3: "Keyboard"
    }
    product_descriptions = {
        1: "High-performance laptop with 16GB RAM and 512GB SSD",
        2: "Ergonomic wireless mouse with precision tracking",
        3: "Mechanical keyboard with RGB backlighting"
    }
    
    name = product_names.get(product_id, f"Product {product_id}")
    description = product_descriptions.get(product_id, "Product description not available")
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Product {product_id} - {name}</title>
        <meta charset="utf-8">
    </head>
    <body>
        <h1>Product {product_id}: {name}</h1>
        <p>{description}</p>
        <p><strong>Price:</strong> ${product_id * 100}.00</p>
        <button id="add-to-cart">Add to Cart</button>
        <br><br>
        <a href="/products" id="back-link">Back to Products</a>
    </body>
    </html>
    """


@app.get("/login", response_class=HTMLResponse)
async def login_form():
    """登录页 - 包含表单"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Login</title>
        <meta charset="utf-8">
    </head>
    <body>
        <h1>Login</h1>
        <form method="POST" action="/login">
            <div>
                <label for="username">Username:</label>
                <input type="text" name="username" id="username" placeholder="Enter username" required>
            </div>
            <div>
                <label for="password">Password:</label>
                <input type="password" name="password" id="password" placeholder="Enter password" required>
            </div>
            <button type="submit" id="login-btn">Login</button>
        </form>
        <br>
        <a href="/" id="home-link">Back to Home</a>
    </body>
    </html>
    """


@app.post("/login")
async def login_submit(username: str = Form(...), password: str = Form(...)):
    """登录提交 - 重定向到仪表板"""
    return RedirectResponse(url="/dashboard", status_code=303)


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """仪表板 - 登录后页面"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dashboard</title>
        <meta charset="utf-8">
    </head>
    <body>
        <h1>Dashboard</h1>
        <p>Welcome! You are logged in.</p>
        <div>
            <h2>Quick Links</h2>
            <ul>
                <li><a href="/products" id="products-link">View Products</a></li>
                <li><a href="/" id="home-link">Home</a></li>
            </ul>
        </div>
    </body>
    </html>
    """


@app.get("/about", response_class=HTMLResponse)
async def about():
    """关于页"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>About</title>
        <meta charset="utf-8">
    </head>
    <body>
        <h1>About Mock Site</h1>
        <p>This is a mock website created for testing the WebExplorer Agent.</p>
        <p>It contains various page types to test different navigation scenarios:</p>
        <ul>
            <li>Multi-level navigation (products)</li>
            <li>Form submission (login)</li>
            <li>Dead ends (pages with no links)</li>
            <li>Loops (circular navigation)</li>
        </ul>
        <a href="/" id="home-link">Back to Home</a>
    </body>
    </html>
    """


@app.get("/deadend", response_class=HTMLResponse)
async def deadend():
    """死胡同页 - 无链接,用于测试回溯功能"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dead End</title>
        <meta charset="utf-8">
    </head>
    <body>
        <h1>Dead End</h1>
        <p>This page has no links. You need to go back.</p>
        <p>Use your browser's back button or the agent's backtracking capability.</p>
    </body>
    </html>
    """


@app.get("/loop-a", response_class=HTMLResponse)
async def loop_a():
    """环路页A - 链接到B,用于测试循环检测"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Loop A</title>
        <meta charset="utf-8">
    </head>
    <body>
        <h1>Loop Page A</h1>
        <p>This page links to Loop Page B.</p>
        <a href="/loop-b" id="to-b">Go to Loop B</a>
        <br><br>
        <a href="/" id="home-link">Back to Home</a>
    </body>
    </html>
    """


@app.get("/loop-b", response_class=HTMLResponse)
async def loop_b():
    """环路页B - 链接到A,形成循环"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Loop B</title>
        <meta charset="utf-8">
    </head>
    <body>
        <h1>Loop Page B</h1>
        <p>This page links back to Loop Page A, creating a loop.</p>
        <a href="/loop-a" id="to-a">Go to Loop A</a>
        <br><br>
        <a href="/" id="home-link">Back to Home</a>
    </body>
    </html>
    """


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "ok", "message": "Mock server is running"}


if __name__ == "__main__":
    print("=" * 60)
    print("Starting Mock Server for WebExplorer Agent Testing")
    print("=" * 60)
    print("Server URL: http://127.0.0.1:8080")
    print("Health Check: http://127.0.0.1:8080/health")
    print("=" * 60)
    print("\nAvailable pages:")
    print("  / - Home page")
    print("  /products - Product list")
    print("  /products/1-3 - Product details")
    print("  /login - Login form")
    print("  /dashboard - Dashboard (after login)")
    print("  /about - About page")
    print("  /deadend - Dead end page (no links)")
    print("  /loop-a, /loop-b - Loop test pages")
    print("=" * 60)
    
    uvicorn.run(app, host="127.0.0.1", port=8080, log_level="info")
