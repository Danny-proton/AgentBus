/**
 * AgentBus 前端应用
 */

class AgentBusApp {
    constructor() {
        this.ws = null;
        this.sessionId = null;
        this.uploadedFiles = [];
        this.isBashMode = false;
        this.selectedVm = 'local';
        
        this.init();
    }
    
    init() {
        // DOM 元素
        this.chatContainer = document.getElementById('chat-container');
        this.terminalOutput = document.getElementById('terminal-output');
        this.chatInput = document.getElementById('chat-input');
        this.sendBtn = document.getElementById('send-btn');
        this.uploadBtn = document.getElementById('upload-btn');
        this.fileInput = document.getElementById('file-input');
        this.vmSelect = document.getElementById('vm-select');
        this.vmConfig = document.getElementById('vm-config');
        this.modeRadios = document.querySelectorAll('input[name="mode"]');
        this.modelSelect = document.getElementById('model-select');
        
        // 绑定事件
        this.bindEvents();
        
        // 初始化连接
        this.connectWebSocket();
        
        // 显示欢迎消息
        this.showWelcomeMessage();
    }
    
    bindEvents() {
        // 发送消息
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.chatInput.addEventListener('keydown', (e) => this.handleInputKeydown(e));
        
        // 文件上传
        this.uploadBtn.addEventListener('click', () => this.fileInput.click());
        this.fileInput.addEventListener('change', (e) => this.handleFileUpload(e));
        
        // 虚拟机选择
        this.vmSelect.addEventListener('change', (e) => this.handleVmChange(e));
        
        // 执行模式
        this.modeRadios.forEach(radio => {
            radio.addEventListener('change', (e) => this.handleModeChange(e));
        });
        
        // 快捷操作
        document.querySelectorAll('.quick-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.handleQuickAction(e));
        });
        
        // 终端操作
        document.getElementById('terminal-clear-btn').addEventListener('click', () => this.clearTerminal());
        document.getElementById('terminal-copy-btn').addEventListener('click', () => this.copyTerminal());
        document.getElementById('new-chat-btn').addEventListener('click', () => this.newChat());
        document.getElementById('clear-chat-btn').addEventListener('click', () => this.clearChat());
        
        // WebSocket 重连
        window.addEventListener('beforeunload', () => this.disconnectWebSocket());
    }
    
    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/agent`;
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('WebSocket 连接成功');
            this.showToast('已连接到 AgentBus', 'success');
        };
        
        this.ws.onmessage = (event) => {
            this.handleWebSocketMessage(event.data);
        };
        
        this.ws.onclose = () => {
            console.log('WebSocket 连接关闭，尝试重连...');
            this.showToast('连接断开，3秒后重连...', 'warning');
            setTimeout(() => this.connectWebSocket(), 3000);
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket 错误:', error);
            this.showToast('连接错误', 'error');
        };
    }
    
    disconnectWebSocket() {
        if (this.ws) {
            this.ws.close();
        }
    }
    
    handleWebSocketMessage(data) {
        try {
            const message = JSON.parse(data);
            
            switch (message.type) {
                case 'session_created':
                    this.sessionId = message.session_id;
                    this.showToast(`会话已创建: ${message.session_id}`, 'success');
                    break;
                    
                case 'chunk':
                    this.handleChunk(message.data, message.done);
                    break;
                    
                case 'interrupted':
                    this.showToast('执行被中断', 'warning');
                    break;
                    
                case 'error':
                    this.showToast(message.content || '发生错误', 'error');
                    this.addTerminalLine(message.content, 'error');
                    break;
                    
                case 'heartbeat':
                    // 心跳响应，忽略
                    break;
                    
                case 'approval_received':
                    this.showToast(`工具调用已${message.approved ? '批准' : '拒绝'}`, 'success');
                    break;
                    
                default:
                    console.log('未知消息类型:', message.type);
            }
        } catch (error) {
            console.error('解析消息失败:', error);
        }
    }
    
    handleChunk(content, done) {
        if (!done) {
            // 正在流式输出，添加到终端
            this.addTerminalLine(content, 'output');
        } else {
            // 输出完成
            this.showToast('响应生成完成', 'success');
        }
    }
    
    sendMessage() {
        const content = this.chatInput.value.trim();
        
        if (!content) {
            this.showToast('请输入消息', 'warning');
            return;
        }
        
        if (!this.sessionId && this.ws.readyState !== WebSocket.OPEN) {
            this.showToast('连接未就绪', 'error');
            return;
        }
        
        // 构建消息
        let finalContent = content;
        
        // 添加前缀（根据模式）
        if (this.isBashMode) {
            finalContent = '! ' + finalContent;
        }
        
        // 添加文件 URL
        if (this.uploadedFiles.length > 0) {
            const fileUrls = this.uploadedFiles.map(f => f.url).join(' ');
            finalContent = fileUrls + ' ' + finalContent;
            this.uploadedFiles = []; // 清空已上传文件
        }
        
        // 显示用户消息
        this.addMessage(content, 'user');
        
        // 清空输入框
        this.chatInput.value = '';
        
        // 通过 WebSocket 发送
        if (this.ws.readyState === WebSocket.OPEN) {
            // 如果没有会话，先初始化
            if (!this.sessionId) {
                this.ws.send(JSON.stringify({
                    type: 'init',
                    session_id: null,
                    workspace: this.getWorkspace()
                }));
            }
            
            // 发送消息
            this.ws.send(JSON.stringify({
                type: 'user_message',
                content: finalContent,
                model: this.modelSelect.value,
                stream: true
            }));
            
            // 在终端显示命令
            this.addTerminalLine(`$ ${finalContent}`, 'command');
        } else {
            this.showToast('连接已断开', 'error');
        }
    }
    
    handleInputKeydown(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            this.sendMessage();
        }
    }
    
    handleFileUpload(e) {
        const files = e.target.files;
        
        for (let file of files) {
            // 模拟上传到服务器（实际应调用后端 API）
            const mockUrl = `file:///workspace/${file.name}`;
            this.uploadedFiles.push({
                name: file.name,
                url: mockUrl
            });
            
            // 在输入框中添加 URL
            this.chatInput.value += mockUrl + ' ';
            this.showToast(`文件已添加: ${file.name}`, 'success');
        }
        
        // 清空 file input，允许重复选择同一文件
        e.target.value = '';
    }
    
    handleVmChange(e) {
        this.selectedVm = e.target.value;
        
        if (this.selectedVm === 'remote') {
            this.vmConfig.style.display = 'block';
        } else {
            this.vmConfig.style.display = 'none';
        }
        
        // 在终端显示切换信息
        this.addTerminalLine(`已切换到${this.selectedVm === 'local' ? '本地' : '远程'}环境`, 'system');
    }
    
    handleModeChange(e) {
        this.isBashMode = e.target.value === 'bash';
        
        const modeText = this.isBashMode ? '强制 Bash 模式' : '对话模式';
        this.showToast(`已切换到${modeText}`, 'success');
        
        // 在终端显示
        this.addTerminalLine(`模式: ${modeText}`, 'system');
    }
    
    handleQuickAction(e) {
        const action = e.target.dataset.action;
        this.chatInput.value = action + ' ';
        this.chatInput.focus();
    }
    
    handleInterrupt() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'interrupt'
            }));
            this.showToast('已发送中断信号', 'warning');
        }
    }
    
    getWorkspace() {
        if (this.selectedVm === 'local') {
            return '/workspace';
        } else {
            const host = document.getElementById('vm-host').value;
            return `ssh://${host}/workspace`;
        }
    }
    
    // UI 辅助方法
    addMessage(content, role) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        
        // 处理 Markdown
        const formattedContent = this.formatMarkdown(content);
        messageDiv.innerHTML = formattedContent;
        
        this.chatContainer.appendChild(messageDiv);
        this.chatContainer.scrollTop = this.chatContainer.scrollHeight;
    }
    
    formatMarkdown(text) {
        // 简单的 Markdown 格式化
        let html = this.escapeHtml(text);
        
        // 代码块
        html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
        
        // 行内代码
        html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
        
        // 粗体
        html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        
        // 斜体
        html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
        
        // 换行
        html = html.replace(/\n/g, '<br>');
        
        return html;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    addTerminalLine(content, type = 'output') {
        const lineDiv = document.createElement('div');
        lineDiv.className = `terminal-line ${type}`;
        lineDiv.textContent = content;
        
        this.terminalOutput.appendChild(lineDiv);
        this.terminalOutput.scrollTop = this.terminalOutput.scrollHeight;
    }
    
    clearTerminal() {
        this.terminalOutput.innerHTML = '';
        this.showToast('终端已清空', 'success');
    }
    
    copyTerminal() {
        const content = this.terminalOutput.innerText;
        navigator.clipboard.writeText(content).then(() => {
            this.showToast('已复制到剪贴板', 'success');
        }).catch(() => {
            this.showToast('复制失败', 'error');
        });
    }
    
    newChat() {
        this.sessionId = null;
        this.chatContainer.innerHTML = '';
        this.uploadedFiles = [];
        this.showWelcomeMessage();
        this.showToast('新建对话', 'success');
    }
    
    clearChat() {
        this.chatContainer.innerHTML = '';
        this.uploadedFiles = [];
        this.showToast('对话已清空', 'success');
    }
    
    showWelcomeMessage() {
        const welcomeText = `🤖 AgentBus 已就绪！

我可以帮助你：
- 💬 进行 AI 对话
- 💻 执行 Bash 命令
- 📝 编写和调试代码
- 🔍 分析代码库

使用方法：
- 直接输入消息进行对话
- 选择"强制 Bash (!)"模式执行命令
- 点击 📎 上传文件
- 使用快捷指令快速操作

开始你的对话吧！`;
        
        this.addMessage(welcomeText, 'system');
    }
    
    showToast(message, type = 'success') {
        const toast = document.getElementById('toast');
        toast.textContent = message;
        toast.className = `toast ${type} show`;
        
        setTimeout(() => {
            toast.className = 'toast';
        }, 3000);
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.agentBusApp = new AgentBusApp();
});
