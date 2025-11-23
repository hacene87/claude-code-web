/**
 * Claude Code Web - Frontend Application
 */

class ClaudeCodeWeb {
    constructor() {
        this.ws = null;
        this.clientId = this.generateClientId();
        this.conversationId = null;
        this.workspace = '.';
        this.isStreaming = false;
        this.autoScroll = true;
        this.currentStreamContent = '';

        this.init();
    }

    generateClientId() {
        return 'client_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    init() {
        this.bindElements();
        this.bindEvents();
        this.connectWebSocket();
        this.loadSystemInfo();
        this.loadConversations();

        // Configure marked.js for markdown
        if (typeof marked !== 'undefined') {
            marked.setOptions({
                highlight: function(code, lang) {
                    if (typeof hljs !== 'undefined' && lang && hljs.getLanguage(lang)) {
                        return hljs.highlight(code, { language: lang }).value;
                    }
                    return code;
                },
                breaks: true,
                gfm: true
            });
        }
    }

    bindElements() {
        // Sidebar elements
        this.statusIndicator = document.getElementById('status-indicator');
        this.statusDot = this.statusIndicator.querySelector('.status-dot');
        this.statusText = this.statusIndicator.querySelector('.status-text');
        this.workspaceInput = document.getElementById('workspace-input');
        this.workspaceInfo = document.getElementById('workspace-info');
        this.conversationsList = document.getElementById('conversations-list');
        this.claudeStatus = document.getElementById('claude-status');

        // Main content elements
        this.messagesContainer = document.getElementById('messages-container');
        this.messagesList = document.getElementById('messages-list');
        this.welcomeMessage = document.getElementById('welcome-message');
        this.messageInput = document.getElementById('message-input');
        this.sendBtn = document.getElementById('send-btn');
        this.cancelBtn = document.getElementById('cancel-btn');
        this.charCount = document.getElementById('char-count');
        this.currentConvTitle = document.getElementById('current-conv-title');

        // Buttons
        this.newConvBtn = document.getElementById('new-conv-btn');
        this.clearBtn = document.getElementById('clear-btn');
        this.browseBtn = document.getElementById('browse-btn');
        this.settingsBtn = document.getElementById('settings-btn');

        // Modals
        this.settingsModal = document.getElementById('settings-modal');
        this.fileBrowserModal = document.getElementById('file-browser-modal');
        this.fileList = document.getElementById('file-list');
        this.browserPath = document.getElementById('browser-path');
    }

    bindEvents() {
        // Message input
        this.messageInput.addEventListener('input', () => this.handleInputChange());
        this.messageInput.addEventListener('keydown', (e) => this.handleKeyDown(e));

        // Send/Cancel buttons
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.cancelBtn.addEventListener('click', () => this.cancelStream());

        // New conversation
        this.newConvBtn.addEventListener('click', () => this.newConversation());

        // Clear messages
        this.clearBtn.addEventListener('click', () => this.clearMessages());

        // Workspace
        this.workspaceInput.addEventListener('change', () => {
            this.workspace = this.workspaceInput.value;
        });
        this.browseBtn.addEventListener('click', () => this.openFileBrowser());

        // Settings
        this.settingsBtn.addEventListener('click', () => this.openSettings());

        // Quick actions
        document.querySelectorAll('.quick-action').forEach(btn => {
            btn.addEventListener('click', () => {
                const action = btn.dataset.action;
                this.messageInput.value = action;
                this.sendMessage();
            });
        });

        // Modal close handlers
        document.querySelectorAll('.modal-close, .modal-backdrop').forEach(el => {
            el.addEventListener('click', (e) => {
                if (e.target === el) {
                    el.closest('.modal').classList.add('hidden');
                }
            });
        });

        // File browser
        document.getElementById('browser-go').addEventListener('click', () => {
            this.loadDirectoryContents(this.browserPath.value);
        });
        document.getElementById('browser-select').addEventListener('click', () => {
            this.selectWorkspace();
        });
        document.getElementById('browser-cancel').addEventListener('click', () => {
            this.fileBrowserModal.classList.add('hidden');
        });

        // Theme selection
        document.getElementById('theme-select').addEventListener('change', (e) => {
            document.body.setAttribute('data-theme', e.target.value);
            localStorage.setItem('theme', e.target.value);
        });

        // Load saved theme
        const savedTheme = localStorage.getItem('theme') || 'dark';
        document.body.setAttribute('data-theme', savedTheme);
        document.getElementById('theme-select').value = savedTheme;
    }

    // WebSocket connection
    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/${this.clientId}`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            this.updateStatus('connected', 'Connected');
            console.log('WebSocket connected');
        };

        this.ws.onclose = () => {
            this.updateStatus('error', 'Disconnected');
            console.log('WebSocket disconnected');
            // Reconnect after 3 seconds
            setTimeout(() => this.connectWebSocket(), 3000);
        };

        this.ws.onerror = (error) => {
            this.updateStatus('error', 'Connection error');
            console.error('WebSocket error:', error);
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };
    }

    handleWebSocketMessage(data) {
        switch (data.event) {
            case 'chunk':
                this.handleStreamChunk(data);
                break;
            case 'complete':
                this.handleStreamComplete(data);
                break;
            case 'error':
                this.handleError(data);
                break;
            case 'message_received':
                // Message acknowledged
                break;
            case 'subscribed':
            case 'unsubscribed':
                // Subscription events
                break;
            case 'cancelled':
                this.handleStreamCancelled();
                break;
        }
    }

    handleStreamChunk(data) {
        const chunk = data.data;

        if (chunk.type === 'text') {
            this.currentStreamContent += chunk.content;
            this.updateStreamingMessage(this.currentStreamContent);
        } else if (chunk.type === 'tool_use') {
            this.appendToolUse(chunk);
        } else if (chunk.type === 'status') {
            this.updateStreamingStatus(chunk.content);
        }
    }

    handleStreamComplete(data) {
        this.isStreaming = false;
        this.toggleStreamingUI(false);

        // Save the complete message to conversation
        if (this.currentStreamContent) {
            this.finalizeStreamingMessage();
        }

        this.currentStreamContent = '';
    }

    handleStreamCancelled() {
        this.isStreaming = false;
        this.toggleStreamingUI(false);
        this.appendSystemMessage('Request cancelled');
        this.currentStreamContent = '';
    }

    handleError(data) {
        this.isStreaming = false;
        this.toggleStreamingUI(false);
        this.appendErrorMessage(data.message || 'An error occurred');
        this.currentStreamContent = '';
    }

    updateStatus(status, text) {
        this.statusDot.className = 'status-dot ' + status;
        this.statusText.textContent = text;
    }

    // API calls
    async loadSystemInfo() {
        try {
            const response = await fetch('/api/system');
            const data = await response.json();

            if (data.claude_code_installed) {
                this.claudeStatus.textContent = '✓ ' + (data.claude_code_version || 'Installed');
                this.claudeStatus.className = 'info-value success';
            } else {
                this.claudeStatus.textContent = '✗ Not installed';
                this.claudeStatus.className = 'info-value error';
            }
        } catch (error) {
            this.claudeStatus.textContent = '✗ Error';
            this.claudeStatus.className = 'info-value error';
        }
    }

    async loadConversations() {
        try {
            const response = await fetch('/api/conversations');
            const conversations = await response.json();

            this.conversationsList.innerHTML = '';
            conversations.forEach(conv => {
                const item = this.createConversationItem(conv);
                this.conversationsList.appendChild(item);
            });
        } catch (error) {
            console.error('Failed to load conversations:', error);
        }
    }

    createConversationItem(conv) {
        const item = document.createElement('div');
        item.className = 'conversation-item' + (conv.id === this.conversationId ? ' active' : '');
        item.dataset.id = conv.id;

        const title = conv.messages && conv.messages.length > 0
            ? conv.messages[0].content.substring(0, 30) + '...'
            : 'New conversation';

        const date = new Date(conv.updated_at).toLocaleDateString();

        item.innerHTML = `
            <div class="conversation-title">${this.escapeHtml(title)}</div>
            <div class="conversation-meta">${date} • ${conv.messages?.length || 0} messages</div>
        `;

        item.addEventListener('click', () => this.loadConversation(conv.id));

        return item;
    }

    async loadConversation(convId) {
        try {
            const response = await fetch(`/api/conversations/${convId}`);
            const conv = await response.json();

            this.conversationId = convId;
            this.workspace = conv.workspace;
            this.workspaceInput.value = conv.workspace;

            // Clear and reload messages
            this.clearMessageDisplay();

            conv.messages.forEach(msg => {
                if (msg.role === 'user') {
                    this.appendUserMessage(msg.content);
                } else {
                    this.appendAssistantMessage(msg.content);
                }
            });

            // Update active state
            document.querySelectorAll('.conversation-item').forEach(item => {
                item.classList.toggle('active', item.dataset.id === convId);
            });

            // Subscribe to conversation updates
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({
                    action: 'subscribe',
                    conversation_id: convId
                }));
            }

            this.currentConvTitle.textContent = `Conversation ${convId.substring(0, 8)}...`;

        } catch (error) {
            console.error('Failed to load conversation:', error);
        }
    }

    // Message handling
    sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || this.isStreaming) return;

        // Hide welcome message
        if (this.welcomeMessage) {
            this.welcomeMessage.style.display = 'none';
        }

        // Append user message
        this.appendUserMessage(message);

        // Clear input
        this.messageInput.value = '';
        this.handleInputChange();

        // Start streaming
        this.isStreaming = true;
        this.currentStreamContent = '';
        this.toggleStreamingUI(true);

        // Create streaming message placeholder
        this.createStreamingMessage();

        // Send via WebSocket
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                action: 'chat',
                message: message,
                workspace: this.workspace,
                conversation_id: this.conversationId
            }));
        } else {
            this.handleError({ message: 'WebSocket not connected' });
        }
    }

    cancelStream() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN && this.conversationId) {
            this.ws.send(JSON.stringify({
                action: 'cancel',
                conversation_id: this.conversationId
            }));
        }
    }

    appendUserMessage(content) {
        const messageEl = document.createElement('div');
        messageEl.className = 'message user';
        messageEl.innerHTML = `
            <div class="message-header">
                <div class="message-avatar">👤</div>
                <span class="message-author">You</span>
                <span class="message-time">${this.formatTime(new Date())}</span>
            </div>
            <div class="message-content">${this.escapeHtml(content)}</div>
        `;
        this.messagesList.appendChild(messageEl);
        this.scrollToBottom();
    }

    appendAssistantMessage(content) {
        const messageEl = document.createElement('div');
        messageEl.className = 'message assistant';
        messageEl.innerHTML = `
            <div class="message-header">
                <div class="message-avatar">⚡</div>
                <span class="message-author">Claude</span>
                <span class="message-time">${this.formatTime(new Date())}</span>
            </div>
            <div class="message-content">${this.renderMarkdown(content)}</div>
        `;
        this.messagesList.appendChild(messageEl);
        this.scrollToBottom();
    }

    createStreamingMessage() {
        const messageEl = document.createElement('div');
        messageEl.className = 'message assistant streaming';
        messageEl.id = 'streaming-message';
        messageEl.innerHTML = `
            <div class="message-header">
                <div class="message-avatar">⚡</div>
                <span class="message-author">Claude</span>
                <span class="message-time">${this.formatTime(new Date())}</span>
            </div>
            <div class="message-content">
                <div class="streaming-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;
        this.messagesList.appendChild(messageEl);
        this.scrollToBottom();
    }

    updateStreamingMessage(content) {
        const messageEl = document.getElementById('streaming-message');
        if (messageEl) {
            const contentEl = messageEl.querySelector('.message-content');
            contentEl.innerHTML = this.renderMarkdown(content);
            this.scrollToBottom();
        }
    }

    finalizeStreamingMessage() {
        const messageEl = document.getElementById('streaming-message');
        if (messageEl) {
            messageEl.classList.remove('streaming');
            messageEl.id = '';

            // Apply syntax highlighting
            messageEl.querySelectorAll('pre code').forEach((block) => {
                if (typeof hljs !== 'undefined') {
                    hljs.highlightElement(block);
                }
            });
        }
    }

    appendToolUse(toolData) {
        const toolEl = document.createElement('div');
        toolEl.className = 'tool-use';
        toolEl.innerHTML = `
            <div class="tool-use-header">
                🔧 Using: ${this.escapeHtml(toolData.metadata?.tool_name || 'tool')}
            </div>
            <pre><code>${this.escapeHtml(toolData.content)}</code></pre>
        `;

        const streamingEl = document.getElementById('streaming-message');
        if (streamingEl) {
            const contentEl = streamingEl.querySelector('.message-content');
            contentEl.appendChild(toolEl);
        }
    }

    updateStreamingStatus(status) {
        // Could show status in a separate element
        console.log('Status:', status);
    }

    appendSystemMessage(content) {
        const messageEl = document.createElement('div');
        messageEl.className = 'message system';
        messageEl.innerHTML = `
            <div class="message-content" style="text-align: center; color: var(--text-muted);">
                ${this.escapeHtml(content)}
            </div>
        `;
        this.messagesList.appendChild(messageEl);
    }

    appendErrorMessage(content) {
        const messageEl = document.createElement('div');
        messageEl.className = 'message error';
        messageEl.innerHTML = `
            <div class="message-content" style="border-color: var(--danger-color); color: var(--danger-color);">
                ⚠️ ${this.escapeHtml(content)}
            </div>
        `;
        this.messagesList.appendChild(messageEl);
        this.scrollToBottom();
    }

    // UI helpers
    toggleStreamingUI(streaming) {
        this.sendBtn.classList.toggle('hidden', streaming);
        this.cancelBtn.classList.toggle('hidden', !streaming);
        this.messageInput.disabled = streaming;
    }

    handleInputChange() {
        // Auto-resize textarea
        this.messageInput.style.height = 'auto';
        this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 200) + 'px';

        // Update character count
        this.charCount.textContent = this.messageInput.value.length;
    }

    handleKeyDown(e) {
        if (e.key === 'Enter' && e.ctrlKey) {
            e.preventDefault();
            this.sendMessage();
        }
    }

    newConversation() {
        this.conversationId = null;
        this.clearMessageDisplay();
        this.currentConvTitle.textContent = 'New Conversation';

        // Show welcome message
        if (this.welcomeMessage) {
            this.welcomeMessage.style.display = 'block';
        }

        // Deselect all conversations
        document.querySelectorAll('.conversation-item').forEach(item => {
            item.classList.remove('active');
        });
    }

    clearMessages() {
        this.clearMessageDisplay();
        if (this.welcomeMessage) {
            this.welcomeMessage.style.display = 'block';
        }
    }

    clearMessageDisplay() {
        const messages = this.messagesList.querySelectorAll('.message');
        messages.forEach(m => m.remove());
    }

    scrollToBottom() {
        if (this.autoScroll) {
            this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        }
    }

    // File browser
    openFileBrowser() {
        this.fileBrowserModal.classList.remove('hidden');
        this.browserPath.value = this.workspace || '~';
        this.loadDirectoryContents(this.browserPath.value);
    }

    async loadDirectoryContents(path) {
        try {
            const response = await fetch(`/api/workspaces?base_path=${encodeURIComponent(path)}`);
            const workspaces = await response.json();

            this.fileList.innerHTML = '';

            // Add parent directory
            const parentItem = document.createElement('div');
            parentItem.className = 'file-item';
            parentItem.innerHTML = `
                <span class="file-icon">📁</span>
                <span class="file-name">..</span>
            `;
            parentItem.addEventListener('click', () => {
                const parent = path.split('/').slice(0, -1).join('/') || '/';
                this.browserPath.value = parent;
                this.loadDirectoryContents(parent);
            });
            this.fileList.appendChild(parentItem);

            // Add directories
            workspaces.forEach(ws => {
                const item = document.createElement('div');
                item.className = 'file-item';
                item.dataset.path = ws.path;

                const gitBadge = ws.is_git_repo ? `<span class="file-meta">git: ${ws.git_branch || 'no branch'}</span>` : '';

                item.innerHTML = `
                    <span class="file-icon">📁</span>
                    <span class="file-name">${this.escapeHtml(ws.name)}</span>
                    ${gitBadge}
                `;

                item.addEventListener('click', () => {
                    // Toggle selection
                    document.querySelectorAll('.file-item').forEach(i => i.classList.remove('selected'));
                    item.classList.add('selected');
                    this.browserPath.value = ws.path;
                });

                item.addEventListener('dblclick', () => {
                    this.browserPath.value = ws.path;
                    this.loadDirectoryContents(ws.path);
                });

                this.fileList.appendChild(item);
            });

        } catch (error) {
            console.error('Failed to load directory:', error);
            this.fileList.innerHTML = `<div class="file-item">Error loading directory</div>`;
        }
    }

    selectWorkspace() {
        this.workspace = this.browserPath.value;
        this.workspaceInput.value = this.workspace;
        this.fileBrowserModal.classList.add('hidden');
        this.workspaceInfo.textContent = `Selected: ${this.workspace}`;
    }

    // Settings
    openSettings() {
        this.settingsModal.classList.remove('hidden');
    }

    // Utility functions
    renderMarkdown(content) {
        if (typeof marked !== 'undefined') {
            return marked.parse(content);
        }
        return this.escapeHtml(content).replace(/\n/g, '<br>');
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    formatTime(date) {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
}

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    window.app = new ClaudeCodeWeb();
});
