"""
Web管理界面静态文件
提供插件和渠道的Web管理界面
"""

# 管理界面HTML模板
MANAGEMENT_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AgentBus 管理界面</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #f5f5f5;
            color: #333;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .tabs {
            display: flex;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }
        
        .tab {
            flex: 1;
            padding: 15px 20px;
            background: white;
            border: none;
            cursor: pointer;
            font-size: 16px;
            transition: all 0.3s ease;
        }
        
        .tab.active {
            background: #667eea;
            color: white;
        }
        
        .tab:hover {
            background: #f0f0f0;
        }
        
        .tab.active:hover {
            background: #5a67d8;
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
        
        .card {
            background: white;
            border-radius: 10px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .card h3 {
            margin-bottom: 15px;
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        
        .status-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
            text-transform: uppercase;
        }
        
        .status-active {
            background: #d4edda;
            color: #155724;
        }
        
        .status-inactive {
            background: #f8d7da;
            color: #721c24;
        }
        
        .status-loading {
            background: #fff3cd;
            color: #856404;
        }
        
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            margin: 2px;
            transition: all 0.3s ease;
        }
        
        .btn-primary {
            background: #667eea;
            color: white;
        }
        
        .btn-primary:hover {
            background: #5a67d8;
        }
        
        .btn-success {
            background: #28a745;
            color: white;
        }
        
        .btn-success:hover {
            background: #218838;
        }
        
        .btn-danger {
            background: #dc3545;
            color: white;
        }
        
        .btn-danger:hover {
            background: #c82333;
        }
        
        .btn-warning {
            background: #ffc107;
            color: #212529;
        }
        
        .btn-warning:hover {
            background: #e0a800;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        
        .item {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 10px;
        }
        
        .item-header {
            display: flex;
            justify-content: between;
            align-items: center;
            margin-bottom: 10px;
        }
        
        .item-title {
            font-weight: bold;
            color: #333;
        }
        
        .item-description {
            color: #666;
            font-size: 14px;
            margin-bottom: 10px;
        }
        
        .item-actions {
            display: flex;
            gap: 5px;
            flex-wrap: wrap;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }
        
        .stat-label {
            color: #666;
            margin-top: 5px;
        }
        
        .loading {
            text-align: center;
            padding: 20px;
            color: #666;
        }
        
        .error {
            background: #f8d7da;
            color: #721c24;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
        }
        
        .success {
            background: #d4edda;
            color: #155724;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
        }
        
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
        }
        
        .modal-content {
            background-color: white;
            margin: 15% auto;
            padding: 20px;
            border-radius: 10px;
            width: 80%;
            max-width: 500px;
        }
        
        .close {
            color: #aaa;
            float: right;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
        }
        
        .close:hover {
            color: #000;
        }
        
        .form-group {
            margin-bottom: 15px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        
        .form-group input, .form-group select, .form-group textarea {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        
        .health-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 5px;
        }
        
        .health-healthy {
            background: #28a745;
        }
        
        .health-warning {
            background: #ffc107;
        }
        
        .health-error {
            background: #dc3545;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 AgentBus 管理界面</h1>
            <p>统一管理插件、渠道和系统服务</p>
        </div>
        
        <div class="tabs">
            <button class="tab active" onclick="showTab('overview')">概览</button>
            <button class="tab" onclick="showTab('plugins')">插件管理</button>
            <button class="tab" onclick="showTab('channels')">渠道管理</button>
            <button class="tab" onclick="showTab('system')">系统状态</button>
        </div>
        
        <!-- 概览页面 -->
        <div id="overview" class="tab-content active">
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number" id="plugin-count">-</div>
                    <div class="stat-label">已加载插件</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="channel-count">-</div>
                    <div class="stat-label">配置渠道</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="tool-count">-</div>
                    <div class="stat-label">可用工具</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="active-channels">-</div>
                    <div class="stat-label">活跃渠道</div>
                </div>
            </div>
            
            <div class="card">
                <h3>🎯 快速操作</h3>
                <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                    <button class="btn btn-primary" onclick="showTab('plugins')">管理插件</button>
                    <button class="btn btn-primary" onclick="showTab('channels')">管理渠道</button>
                    <button class="btn btn-success" onclick="connectAllChannels()">连接所有渠道</button>
                    <button class="btn btn-warning" onclick="reloadAllPlugins()">重载所有插件</button>
                </div>
            </div>
            
            <div class="card">
                <h3>📊 系统状态</h3>
                <div id="system-status">
                    <div class="loading">正在加载系统状态...</div>
                </div>
            </div>
        </div>
        
        <!-- 插件管理页面 -->
        <div id="plugins" class="tab-content">
            <div class="card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h3>🔌 插件管理</h3>
                    <div>
                        <button class="btn btn-primary" onclick="discoverPlugins()">发现插件</button>
                        <button class="btn btn-success" onclick="reloadPlugins()">刷新</button>
                    </div>
                </div>
                
                <div id="plugins-list">
                    <div class="loading">正在加载插件列表...</div>
                </div>
            </div>
        </div>
        
        <!-- 渠道管理页面 -->
        <div id="channels" class="tab-content">
            <div class="card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h3>📡 渠道管理</h3>
                    <div>
                        <button class="btn btn-success" onclick="connectAllChannels()">连接所有</button>
                        <button class="btn btn-warning" onclick="disconnectAllChannels()">断开所有</button>
                        <button class="btn btn-primary" onclick="reloadChannels()">刷新</button>
                    </div>
                </div>
                
                <div id="channels-list">
                    <div class="loading">正在加载渠道列表...</div>
                </div>
            </div>
        </div>
        
        <!-- 系统状态页面 -->
        <div id="system" class="tab-content">
            <div class="card">
                <h3>⚙️ 系统状态</h3>
                <div id="detailed-system-status">
                    <div class="loading">正在加载系统状态...</div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- 插件详情模态框 -->
    <div id="plugin-modal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeModal('plugin-modal')">&times;</span>
            <h3>插件详情</h3>
            <div id="plugin-details">
                <div class="loading">正在加载插件详情...</div>
            </div>
        </div>
    </div>
    
    <!-- 渠道详情模态框 -->
    <div id="channel-modal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeModal('channel-modal')">&times;</span>
            <h3>渠道详情</h3>
            <div id="channel-details">
                <div class="loading">正在加载渠道详情...</div>
            </div>
        </div>
    </div>

    <script>
        // 全局变量
        let plugins = [];
        let channels = [];
        let systemStats = {};
        
        // 页面加载完成后初始化
        document.addEventListener('DOMContentLoaded', function() {
            loadOverview();
            loadPlugins();
            loadChannels();
            loadSystemStatus();
            
            // 定期刷新数据
            setInterval(() => {
                loadOverview();
                loadPlugins();
                loadChannels();
            }, 30000); // 每30秒刷新一次
        });
        
        // 标签页切换
        function showTab(tabName) {
            // 隐藏所有标签页内容
            const contents = document.querySelectorAll('.tab-content');
            contents.forEach(content => content.classList.remove('active'));
            
            // 移除所有标签的激活状态
            const tabs = document.querySelectorAll('.tab');
            tabs.forEach(tab => tab.classList.remove('active'));
            
            // 显示选中的标签页
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
        }
        
        // 加载概览数据
        async function loadOverview() {
            try {
                const [pluginsRes, channelsRes] = await Promise.all([
                    fetch('/api/v1/plugins/'),
                    fetch('/api/v1/channels/')
                ]);
                
                const pluginsData = await pluginsRes.json();
                const channelsData = await channelsRes.json();
                
                document.getElementById('plugin-count').textContent = pluginsData.plugins?.length || 0;
                document.getElementById('channel-count').textContent = channelsData.channels?.length || 0;
                
                // 获取工具数量
                const toolsRes = await fetch('/api/v1/plugins/tools');
                const toolsData = await toolsRes.json();
                document.getElementById('tool-count').textContent = toolsData.tools?.length || 0;
                
                // 获取活跃渠道数量
                const statusRes = await fetch('/api/v1/channels/status/all');
                const statusData = await statusRes.json();
                let activeChannels = 0;
                if (statusData.channels_status) {
                    Object.values(statusData.channels_status).forEach(channel => {
                        Object.values(channel).forEach(account => {
                            if (account.connection_status === 'connected') {
                                activeChannels++;
                            }
                        });
                    });
                }
                document.getElementById('active-channels').textContent = activeChannels;
                
            } catch (error) {
                console.error('加载概览数据失败:', error);
            }
        }
        
        // 加载插件列表
        async function loadPlugins() {
            try {
                const response = await fetch('/api/v1/plugins/');
                const data = await response.json();
                plugins = data.plugins || [];
                
                const container = document.getElementById('plugins-list');
                
                if (plugins.length === 0) {
                    container.innerHTML = '<p>暂无插件</p>';
                    return;
                }
                
                let html = '';
                plugins.forEach(plugin => {
                    html += `
                        <div class="item">
                            <div class="item-header">
                                <div class="item-title">${plugin.name}</div>
                                <span class="status-badge status-${plugin.status}">${plugin.status}</span>
                            </div>
                            <div class="item-description">${plugin.description || '暂无描述'}</div>
                            <div style="font-size: 12px; color: #666;">
                                版本: ${plugin.version} | 作者: ${plugin.author}
                            </div>
                            <div class="item-actions">
                                ${getPluginActionButtons(plugin)}
                            </div>
                        </div>
                    `;
                });
                
                container.innerHTML = html;
                
            } catch (error) {
                console.error('加载插件列表失败:', error);
                document.getElementById('plugins-list').innerHTML = 
                    '<div class="error">加载插件列表失败</div>';
            }
        }
        
        // 获取插件操作按钮
        function getPluginActionButtons(plugin) {
            let buttons = '';
            
            if (plugin.status === 'loaded') {
                buttons += `<button class="btn btn-success" onclick="activatePlugin('${plugin.id}')">激活</button>`;
            } else if (plugin.status === 'active') {
                buttons += `<button class="btn btn-warning" onclick="deactivatePlugin('${plugin.id}')">停用</button>`;
            }
            
            buttons += `<button class="btn btn-primary" onclick="showPluginDetails('${plugin.id}')">详情</button>`;
            buttons += `<button class="btn btn-danger" onclick="unloadPlugin('${plugin.id}')">卸载</button>`;
            
            return buttons;
        }
        
        // 加载渠道列表
        async function loadChannels() {
            try {
                const response = await fetch('/api/v1/channels/');
                const data = await response.json();
                channels = data.channels || [];
                
                // 获取渠道状态
                const statusRes = await fetch('/api/v1/channels/status/all');
                const statusData = await statusRes.json();
                const statusMap = statusData.channels_status || {};
                
                const container = document.getElementById('channels-list');
                
                if (channels.length === 0) {
                    container.innerHTML = '<p>暂无渠道配置</p>';
                    return;
                }
                
                let html = '';
                for (const channelId of channels) {
                    const channelStatus = statusMap[channelId] || {};
                    const accountStatus = Object.values(channelStatus)[0] || {};
                    const isConnected = accountStatus.connection_status === 'connected';
                    
                    html += `
                        <div class="item">
                            <div class="item-header">
                                <div class="item-title">${channelId}</div>
                                <span class="health-indicator health-${isConnected ? 'healthy' : 'error'}"></span>
                                <span class="status-badge status-${isConnected ? 'active' : 'inactive'}">
                                    ${isConnected ? '已连接' : '未连接'}
                                </span>
                            </div>
                            <div class="item-description">渠道ID: ${channelId}</div>
                            <div class="item-actions">
                                ${isConnected ? 
                                    `<button class="btn btn-warning" onclick="disconnectChannel('${channelId}')">断开</button>` :
                                    `<button class="btn btn-success" onclick="connectChannel('${channelId}')">连接</button>`
                                }
                                <button class="btn btn-primary" onclick="showChannelDetails('${channelId}')">详情</button>
                            </div>
                        </div>
                    `;
                }
                
                container.innerHTML = html;
                
            } catch (error) {
                console.error('加载渠道列表失败:', error);
                document.getElementById('channels-list').innerHTML = 
                    '<div class="error">加载渠道列表失败</div>';
            }
        }
        
        // 加载系统状态
        async function loadSystemStatus() {
            try {
                const [healthRes, statsRes] = await Promise.all([
                    fetch('/health'),
                    fetch('/api/v1/plugins/stats')
                ]);
                
                const healthData = await healthRes.json();
                const statsData = await statsRes.json();
                
                // 更新概览页面系统状态
                const systemStatusContainer = document.getElementById('system-status');
                systemStatusContainer.innerHTML = `
                    <div>整体状态: ${healthData.status || '未知'}</div>
                    <div>服务数量: ${Object.keys(healthData.services || {}).length}</div>
                    <div>插件统计: ${statsData.total_plugins || 0} 个插件</div>
                `;
                
                // 更新详细系统状态页面
                const detailedSystemContainer = document.getElementById('detailed-system-status');
                detailedSystemContainer.innerHTML = `
                    <h4>健康检查</h4>
                    <pre>${JSON.stringify(healthData, null, 2)}</pre>
                    <h4>插件统计</h4>
                    <pre>${JSON.stringify(statsData, null, 2)}</pre>
                `;
                
            } catch (error) {
                console.error('加载系统状态失败:', error);
                document.getElementById('system-status').innerHTML = 
                    '<div class="error">加载系统状态失败</div>';
                document.getElementById('detailed-system-status').innerHTML = 
                    '<div class="error">加载详细系统状态失败</div>';
            }
        }
        
        // 插件操作函数
        async function activatePlugin(pluginId) {
            try {
                const response = await fetch(`/api/v1/plugins/${pluginId}/activate`, {
                    method: 'POST'
                });
                
                if (response.ok) {
                    showMessage('success', `插件 ${pluginId} 激活成功`);
                    loadPlugins();
                } else {
                    showMessage('error', `插件 ${pluginId} 激活失败`);
                }
            } catch (error) {
                showMessage('error', `激活插件失败: ${error.message}`);
            }
        }
        
        async function deactivatePlugin(pluginId) {
            try {
                const response = await fetch(`/api/v1/plugins/${pluginId}/deactivate`, {
                    method: 'POST'
                });
                
                if (response.ok) {
                    showMessage('success', `插件 ${pluginId} 停用成功`);
                    loadPlugins();
                } else {
                    showMessage('error', `插件 ${pluginId} 停用失败`);
                }
            } catch (error) {
                showMessage('error', `停用插件失败: ${error.message}`);
            }
        }
        
        async function unloadPlugin(pluginId) {
            if (!confirm(`确定要卸载插件 ${pluginId} 吗？`)) {
                return;
            }
            
            try {
                const response = await fetch(`/api/v1/plugins/${pluginId}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    showMessage('success', `插件 ${pluginId} 卸载成功`);
                    loadPlugins();
                } else {
                    showMessage('error', `插件 ${pluginId} 卸载失败`);
                }
            } catch (error) {
                showMessage('error', `卸载插件失败: ${error.message}`);
            }
        }
        
        // 渠道操作函数
        async function connectChannel(channelId) {
            try {
                const response = await fetch(`/api/v1/channels/${channelId}/connect`, {
                    method: 'POST'
                });
                
                if (response.ok) {
                    showMessage('success', `渠道 ${channelId} 连接成功`);
                    loadChannels();
                } else {
                    showMessage('error', `渠道 ${channelId} 连接失败`);
                }
            } catch (error) {
                showMessage('error', `连接渠道失败: ${error.message}`);
            }
        }
        
        async function disconnectChannel(channelId) {
            try {
                const response = await fetch(`/api/v1/channels/${channelId}/disconnect`, {
                    method: 'POST'
                });
                
                if (response.ok) {
                    showMessage('success', `渠道 ${channelId} 断开成功`);
                    loadChannels();
                } else {
                    showMessage('error', `渠道 ${channelId} 断开失败`);
                }
            } catch (error) {
                showMessage('error', `断开渠道失败: ${error.message}`);
            }
        }
        
        async function connectAllChannels() {
            try {
                const response = await fetch('/api/v1/channels/connect/all', {
                    method: 'POST'
                });
                
                if (response.ok) {
                    showMessage('success', '已尝试连接所有渠道');
                    loadChannels();
                } else {
                    showMessage('error', '连接所有渠道失败');
                }
            } catch (error) {
                showMessage('error', `连接所有渠道失败: ${error.message}`);
            }
        }
        
        async function disconnectAllChannels() {
            try {
                const response = await fetch('/api/v1/channels/disconnect/all', {
                    method: 'POST'
                });
                
                if (response.ok) {
                    showMessage('success', '已断开所有渠道');
                    loadChannels();
                } else {
                    showMessage('error', '断开所有渠道失败');
                }
            } catch (error) {
                showMessage('error', `断开所有渠道失败: ${error.message}`);
            }
        }
        
        // 辅助函数
        async function reloadPlugins() {
            loadPlugins();
            loadOverview();
        }
        
        async function reloadChannels() {
            loadChannels();
            loadOverview();
        }
        
        async function reloadAllPlugins() {
            try {
                showMessage('info', '正在重载所有插件...');
                
                for (const plugin of plugins) {
                    if (plugin.status === 'active') {
                        await fetch(`/api/v1/plugins/${plugin.id}/reload`, {
                            method: 'POST'
                        });
                    }
                }
                
                showMessage('success', '所有插件重载完成');
                loadPlugins();
                loadOverview();
            } catch (error) {
                showMessage('error', `重载插件失败: ${error.message}`);
            }
        }
        
        async function discoverPlugins() {
            try {
                const response = await fetch('/api/v1/plugins/discover');
                const data = await response.json();
                
                showMessage('success', `发现 ${data.discovered_plugins?.length || 0} 个新插件`);
                loadPlugins();
            } catch (error) {
                showMessage('error', `发现插件失败: ${error.message}`);
            }
        }
        
        function showMessage(type, message) {
            // 创建消息元素
            const messageDiv = document.createElement('div');
            messageDiv.className = type;
            messageDiv.textContent = message;
            
            // 添加到页面顶部
            document.body.insertBefore(messageDiv, document.body.firstChild);
            
            // 3秒后移除
            setTimeout(() => {
                messageDiv.remove();
            }, 3000);
        }
        
        function showPluginDetails(pluginId) {
            // 这里可以实现插件详情查看
            alert(`插件详情功能开发中: ${pluginId}`);
        }
        
        function showChannelDetails(channelId) {
            // 这里可以实现渠道详情查看
            alert(`渠道详情功能开发中: ${channelId}`);
        }
        
        function closeModal(modalId) {
            document.getElementById(modalId).style.display = 'none';
        }
        
        // 点击模态框外部关闭
        window.onclick = function(event) {
            const modals = document.querySelectorAll('.modal');
            modals.forEach(modal => {
                if (event.target === modal) {
                    modal.style.display = 'none';
                }
            });
        }
    </script>
</body>
</html>
"""

# 简单的JavaScript API客户端
JS_API_CLIENT = """
// AgentBus API客户端
class AgentBusAPI {
    constructor(baseURL = '') {
        this.baseURL = baseURL;
    }
    
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };
        
        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error(`API请求失败: ${url}`, error);
            throw error;
        }
    }
    
    // 插件相关API
    async getPlugins() {
        return this.request('/api/v1/plugins/');
    }
    
    async getPlugin(pluginId) {
        return this.request(`/api/v1/plugins/${pluginId}`);
    }
    
    async activatePlugin(pluginId) {
        return this.request(`/api/v1/plugins/${pluginId}/activate`, { method: 'POST' });
    }
    
    async deactivatePlugin(pluginId) {
        return this.request(`/api/v1/plugins/${pluginId}/deactivate`, { method: 'POST' });
    }
    
    async unloadPlugin(pluginId) {
        return this.request(`/api/v1/plugins/${pluginId}`, { method: 'DELETE' });
    }
    
    async getPluginTools() {
        return this.request('/api/v1/plugins/tools');
    }
    
    async discoverPlugins() {
        return this.request('/api/v1/plugins/discover');
    }
    
    async getPluginStats() {
        return this.request('/api/v1/plugins/stats');
    }
    
    // 渠道相关API
    async getChannels() {
        return this.request('/api/v1/channels/');
    }
    
    async getChannel(channelId) {
        return this.request(`/api/v1/channels/${channelId}`);
    }
    
    async getChannelStatus(channelId) {
        return this.request(`/api/v1/channels/${channelId}/status`);
    }
    
    async getAllChannelStatus() {
        return this.request('/api/v1/channels/status/all');
    }
    
    async connectChannel(channelId, accountId = null) {
        return this.request(`/api/v1/channels/${channelId}/connect`, {
            method: 'POST',
            body: JSON.stringify({ account_id: accountId })
        });
    }
    
    async disconnectChannel(channelId, accountId = null) {
        return this.request(`/api/v1/channels/${channelId}/disconnect`, {
            method: 'POST',
            body: JSON.stringify({ account_id: accountId })
        });
    }
    
    async connectAllChannels() {
        return this.request('/api/v1/channels/connect/all', { method: 'POST' });
    }
    
    async disconnectAllChannels() {
        return this.request('/api/v1/channels/disconnect/all', { method: 'POST' });
    }
    
    async sendMessage(channelId, messageData) {
        return this.request(`/api/v1/channels/${channelId}/send`, {
            method: 'POST',
            body: JSON.stringify(messageData)
        });
    }
    
    async getChannelTypes() {
        return this.request('/api/v1/channels/types');
    }
    
    async getChannelStats() {
        return this.request('/api/v1/channels/stats');
    }
    
    async getChannelHealth() {
        return this.request('/api/v1/channels/health');
    }
    
    // 系统相关API
    async getHealth() {
        return this.request('/health');
    }
    
    async getAPIInfo() {
        return this.request('/api/info');
    }
}

// 导出API客户端
window.AgentBusAPI = AgentBusAPI;
"""