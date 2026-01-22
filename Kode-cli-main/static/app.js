let sessionId = null;
const chatHistory = document.getElementById('chat-history');
const vmTerminal = document.getElementById('vm-terminal');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const modeSelector = document.getElementById('mode-selector');

// 初始化会话
async function initSession() {
    try {
        const res = await fetch('/api/session', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });
        const data = await res.json();
        sessionId = data.session_id;
        appendChat('system', `会话已启动。当前工作目录: ${data.cwd}`);
        appendTerminal('system', `已连接到本地 Shell 会话。`);
    } catch (e) {
        appendChat('system', `连接后端时出错: ${e}`);
    }
}

// 聊天面板辅助函数
function appendChat(role, content) {
    const div = document.createElement('div');
    div.className = `message ${role}`;

    // 助手/系统消息使用 Markdown 渲染
    if (role === 'assistant' || role === 'system') {
        div.innerHTML = marked.parse(content);
    } else {
        div.textContent = content; // 用户文本通常是纯文本
    }

    chatHistory.appendChild(div);
    chatHistory.scrollTop = chatHistory.scrollHeight;
    return div;
}

// 虚拟机面板辅助函数
function appendTerminal(type, content) {
    const div = document.createElement('div');
    div.className = `terminal-line vm-${type}`;
    div.textContent = content;

    // 如果需要可以处理命令提示符外观，但简单的块也可以
    vmTerminal.appendChild(div);
    vmTerminal.scrollTop = vmTerminal.scrollHeight;
}

// 发送消息
async function sendMessage() {
    const text = messageInput.value.trim();
    if (!text) return;

    let toSend = text;
    const mode = modeSelector.value;

    if (mode === 'bash') {
        toSend = `! ${toSend}`;
    }

    messageInput.value = '';

    // UI 立即更新
    if (mode === 'bash') {
        // 如果是 bash 模式，在聊天中模糊显示，但主要是一个动作
        // 实际上，用户聊天历史通常显示他们输入的内容。
        appendChat('user', text);
    } else {
        appendChat('user', text);
    }

    // 如果不是纯 bash 命令（重定向输出），我们只需为助手创建一个“思考中”的 div
    // 但由于后端生成流，我们将根据块的类型决定将其放在哪里。

    let currentChatDiv = null;

    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: toSend,
                session_id: sessionId
            })
        });

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            buffer += chunk;

            // 手动处理基本的基于行的 SSE 解析（简化版）
            // 真实的 SSE 可能会尴尬地分割行，但通常 python sse-starlette 发送 "data: ...\n\n"
            const lines = buffer.split('\n\n');
            buffer = lines.pop(); // 保留不完整的块

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.slice(6);

                    // 协议: 
                    // stdout: ...
                    // stderr: ...
                    // tool_start: ...
                    // 其他任何内容: 聊天 token

                    if (data.startsWith('stdout: ')) {
                        appendTerminal('stdout', data.slice(8));
                    } else if (data.startsWith('stderr: ')) {
                        appendTerminal('stderr', data.slice(8));
                    } else if (data.startsWith('tool_start: ')) {
                        appendTerminal('cmd', `> 正在执行 ${data.slice(12)}...`);
                    } else {
                        // 正常聊天 token
                        if (!currentChatDiv) {
                            currentChatDiv = appendChat('assistant', '');
                        }
                        // 累积并重新渲染 markdown（对于大流不是最优的，但对于简单的可行）
                        // 注意：要正确执行此操作，我们需要累积状态。
                        // 目前我们只是追加文本。Marked 可能会在部分内容上中断。
                        // 更好：在变量中累积全文，重新渲染 innerHTML。
                        if (!currentChatDiv.dataset.fullText) currentChatDiv.dataset.fullText = '';
                        currentChatDiv.dataset.fullText += data;
                        currentChatDiv.innerHTML = marked.parse(currentChatDiv.dataset.fullText);
                        chatHistory.scrollTop = chatHistory.scrollHeight;
                    }
                }
            }
        }
    } catch (e) {
        appendChat('system', `错误: ${e.message}`);
    }
}

function handleFileUpload(input) {
    if (input.files && input.files[0]) {
        const file = input.files[0];
        const url = `file://${file.name}`;
        messageInput.value = (messageInput.value + ` ${url}`).trim();
    }
}

sendBtn.addEventListener('click', sendMessage);
messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// Start
initSession();
