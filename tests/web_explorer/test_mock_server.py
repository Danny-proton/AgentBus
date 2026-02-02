"""
Mock Server 烟雾测试

验证 Mock Server 的基本功能,不依赖 WebExplorer Agent 实现。
这些测试可以立即运行,用于验证测试基础设施。
"""

import pytest
import httpx
import asyncio


class TestMockServerBasic:
    """测试 Mock Server 基础功能"""
    
    @pytest.mark.asyncio
    async def test_server_health(self, mock_server):
        """测试健康检查端点"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{mock_server}/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "running" in data["message"].lower()
    
    @pytest.mark.asyncio
    async def test_home_page(self, mock_server):
        """测试首页可访问"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{mock_server}/")
            assert response.status_code == 200
            assert "Mock Site" in response.text
            assert "Welcome" in response.text
    
    @pytest.mark.asyncio
    async def test_products_page(self, mock_server):
        """测试产品列表页"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{mock_server}/products")
            assert response.status_code == 200
            assert "Product List" in response.text
            assert "Product 1" in response.text
            assert "Product 2" in response.text
            assert "Product 3" in response.text
    
    @pytest.mark.asyncio
    async def test_product_detail_pages(self, mock_server):
        """测试产品详情页"""
        async with httpx.AsyncClient() as client:
            for product_id in [1, 2, 3]:
                response = await client.get(f"{mock_server}/products/{product_id}")
                assert response.status_code == 200
                assert f"Product {product_id}" in response.text
    
    @pytest.mark.asyncio
    async def test_login_page(self, mock_server):
        """测试登录页"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{mock_server}/login")
            assert response.status_code == 200
            assert "Login" in response.text
            assert "username" in response.text.lower()
            assert "password" in response.text.lower()
    
    @pytest.mark.asyncio
    async def test_about_page(self, mock_server):
        """测试关于页"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{mock_server}/about")
            assert response.status_code == 200
            assert "About" in response.text
    
    @pytest.mark.asyncio
    async def test_deadend_page(self, mock_server):
        """测试死胡同页"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{mock_server}/deadend")
            assert response.status_code == 200
            assert "Dead End" in response.text
            # 验证没有链接(除了可能的样式/脚本)
            assert response.text.count('<a href') == 0
    
    @pytest.mark.asyncio
    async def test_loop_pages(self, mock_server):
        """测试环路页面"""
        async with httpx.AsyncClient() as client:
            # 测试 Loop A
            response_a = await client.get(f"{mock_server}/loop-a")
            assert response_a.status_code == 200
            assert "Loop Page A" in response_a.text
            assert "/loop-b" in response_a.text
            
            # 测试 Loop B
            response_b = await client.get(f"{mock_server}/loop-b")
            assert response_b.status_code == 200
            assert "Loop Page B" in response_b.text
            assert "/loop-a" in response_b.text


class TestMockServerNavigation:
    """测试页面导航链接"""
    
    @pytest.mark.asyncio
    async def test_home_navigation_links(self, mock_server):
        """测试首页包含所有导航链接"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{mock_server}/")
            assert response.status_code == 200
            
            # 验证所有主要链接存在
            assert '/products' in response.text
            assert '/login' in response.text
            assert '/about' in response.text
            assert '/deadend' in response.text
            assert '/loop-a' in response.text
    
    @pytest.mark.asyncio
    async def test_products_links_to_details(self, mock_server):
        """测试产品列表链接到详情页"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{mock_server}/products")
            assert response.status_code == 200
            
            # 验证产品详情链接
            assert '/products/1' in response.text
            assert '/products/2' in response.text
            assert '/products/3' in response.text
            
            # 验证返回首页链接
            assert 'href="/"' in response.text


class TestMockServerForms:
    """测试表单功能"""
    
    @pytest.mark.asyncio
    async def test_login_form_submission(self, mock_server):
        """测试登录表单提交"""
        async with httpx.AsyncClient(follow_redirects=True) as client:
            # 提交登录表单
            response = await client.post(
                f"{mock_server}/login",
                data={"username": "testuser", "password": "testpass"}
            )
            
            assert response.status_code == 200
            # 应该重定向到 dashboard
            assert "Dashboard" in response.text
            assert "Welcome" in response.text
    
    @pytest.mark.asyncio
    async def test_dashboard_page(self, mock_server):
        """测试仪表板页面"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{mock_server}/dashboard")
            assert response.status_code == 200
            assert "Dashboard" in response.text


class TestMockServerDepth:
    """测试页面深度"""
    
    @pytest.mark.asyncio
    async def test_page_depth_levels(self, mock_server):
        """测试不同深度的页面都可访问"""
        async with httpx.AsyncClient() as client:
            # 第1层: 首页
            response = await client.get(f"{mock_server}/")
            assert response.status_code == 200
            
            # 第2层: 产品列表
            response = await client.get(f"{mock_server}/products")
            assert response.status_code == 200
            
            # 第3层: 产品详情
            response = await client.get(f"{mock_server}/products/1")
            assert response.status_code == 200


class TestMockServerEdgeCases:
    """测试边界情况"""
    
    @pytest.mark.asyncio
    async def test_invalid_product_id(self, mock_server):
        """测试无效的产品ID"""
        async with httpx.AsyncClient() as client:
            # 应该仍然返回200,但显示通用产品信息
            response = await client.get(f"{mock_server}/products/999")
            assert response.status_code == 200
            assert "Product 999" in response.text
    
    @pytest.mark.asyncio
    async def test_404_page(self, mock_server):
        """测试不存在的页面"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{mock_server}/nonexistent")
            assert response.status_code == 404
