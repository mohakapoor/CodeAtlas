import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, request, jsonify
from src.chat import CodeAtlasChat

app = Flask(__name__)
chat_engine = CodeAtlasChat()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CodeAtlas Chat</title>
    <style>
        :root {
            --bg-color: #0f1115;
            --chat-bg: #1a1d24;
            --primary: #6366f1;
            --text-main: #e2e8f0;
            --text-muted: #94a3b8;
            --border: #334155;
        }
        body {
            margin: 0;
            padding: 0;
            font-family: 'Inter', -apple-system, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            display: flex;
            justify-content: center;
            height: 100vh;
        }
        .container {
            width: 100%;
            max-width: 900px;
            display: flex;
            flex-direction: column;
            height: 100vh;
            background-color: var(--chat-bg);
            box-shadow: 0 0 20px rgba(0,0,0,0.5);
            border-left: 1px solid var(--border);
            border-right: 1px solid var(--border);
        }
        .header {
            padding: 20px;
            border-bottom: 1px solid var(--border);
            text-align: center;
            background: linear-gradient(135deg, rgba(99,102,241,0.1) 0%, rgba(15,17,21,0) 100%);
        }
        .header h1 {
            margin: 0;
            font-size: 1.5rem;
            color: var(--primary);
        }
        .chat-box {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        .message {
            display: flex;
            flex-direction: column;
            max-width: 85%;
        }
        .message.user {
            align-self: flex-end;
            align-items: flex-end;
        }
        .message.bot {
            align-self: flex-start;
        }
        .bubble {
            padding: 12px 16px;
            border-radius: 12px;
            line-height: 1.5;
            word-wrap: break-word;
        }
        .message.user .bubble {
            background-color: var(--primary);
            color: #fff;
            border-bottom-right-radius: 2px;
        }
        .message.bot .bubble {
            background-color: #2a2f3a;
            border: 1px solid var(--border);
            border-bottom-left-radius: 2px;
        }
        .sources {
            margin-top: 8px;
            font-size: 0.85rem;
            color: var(--text-muted);
            background: #15171c;
            padding: 10px;
            border-radius: 8px;
            border: 1px solid var(--border);
        }
        .sources details summary {
            cursor: pointer;
            outline: none;
            font-weight: bold;
        }
        .sources ul {
            margin: 10px 0 0 0;
            padding-left: 20px;
        }
        .sources li {
            margin-bottom: 4px;
        }
        .input-area {
            padding: 20px;
            border-top: 1px solid var(--border);
            display: flex;
            gap: 10px;
            background-color: var(--chat-bg);
        }
        input[type="text"] {
            flex: 1;
            padding: 12px 16px;
            border-radius: 8px;
            border: 1px solid var(--border);
            background-color: #0f1115;
            color: var(--text-main);
            font-size: 1rem;
            outline: none;
            transition: border-color 0.2s;
        }
        input[type="text"]:focus {
            border-color: var(--primary);
        }
        button {
            padding: 12px 24px;
            border-radius: 8px;
            border: none;
            background-color: var(--primary);
            color: #fff;
            font-size: 1rem;
            font-weight: bold;
            cursor: pointer;
            transition: opacity 0.2s;
        }
        button:hover {
            opacity: 0.9;
        }
        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .typing {
            display: inline-block;
            font-style: italic;
            color: var(--text-muted);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🗺️ CodeAtlas Chat</h1>
        </div>
        <div class="chat-box" id="chat-box">
            <div class="message bot">
                <div class="bubble">Hello! Ask me anything about your codebase. I'll automatically retrieve code and documentation.</div>
            </div>
        </div>
        <div class="input-area">
            <input type="text" id="user-input" placeholder="What does the router do?..." onkeypress="handleEnter(event)">
            <button id="send-btn" onclick="sendMessage()">Send</button>
        </div>
    </div>

    <script>
        const chatBox = document.getElementById('chat-box');
        const userInput = document.getElementById('user-input');
        const sendBtn = document.getElementById('send-btn');

        function handleEnter(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        }

        async function sendMessage() {
            const text = userInput.value.trim();
            if (!text) return;

            // Add user message
            addMessage(text, 'user');
            userInput.value = '';
            
            // Add loading indicator
            sendBtn.disabled = true;
            const loadingId = addLoading();

            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: text })
                });
                
                const data = await response.json();
                
                // Remove loading indicator
                document.getElementById(loadingId).remove();
                
                // Add bot message
                addMessage(data.answer, 'bot', data.sources);
                
            } catch (err) {
                document.getElementById(loadingId).remove();
                addMessage("Error connecting to server.", 'bot');
            } finally {
                sendBtn.disabled = false;
                userInput.focus();
            }
        }

        function addMessage(text, sender, sources = null) {
            const msgDiv = document.createElement('div');
            msgDiv.className = `message ${sender}`;
            
            let innerHTML = `<div class="bubble">${formatText(text)}</div>`;
            
            if (sources && sources.length > 0) {
                let sourceItems = sources.map(s => `<li><strong>[${s.repo}]</strong> ${s.path} (${s.type})</li>`).join('');
                innerHTML += `
                    <div class="sources">
                        <details>
                            <summary>View Retrieved Sources (${sources.length})</summary>
                            <ul>${sourceItems}</ul>
                        </details>
                    </div>
                `;
            }
            
            msgDiv.innerHTML = innerHTML;
            chatBox.appendChild(msgDiv);
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        function addLoading() {
            const id = 'loading-' + Date.now();
            const msgDiv = document.createElement('div');
            msgDiv.id = id;
            msgDiv.className = 'message bot';
            msgDiv.innerHTML = `<div class="bubble"><span class="typing">Thinking and searching codebase...</span></div>`;
            chatBox.appendChild(msgDiv);
            chatBox.scrollTop = chatBox.scrollHeight;
            return id;
        }

        function formatText(text) {
            // Basic regex to handle Markdown bold, newlines, and code blocks
            return text
                .replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>')
                .replace(/```([\\s\\S]*?)```/g, '<pre style="background:#0f1115;padding:10px;border-radius:4px;overflow-x:auto;">$1</pre>')
                .replace(/`([^`]+)`/g, '<code style="background:#0f1115;padding:2px 4px;border-radius:4px;">$1</code>')
                .replace(/\\n/g, '<br>');
        }
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return HTML_TEMPLATE

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    query = data.get("query", "")
    
    if not query:
        return jsonify({"answer": "Empty query", "sources": []}), 400
        
    try:
        response = chat_engine.ask(query)
        
        # CodeAtlasChat now returns formatted sources directly
        sources = response.get("sources", [])
                
        return jsonify({
            "answer": response.get("answer", "No answer generated."),
            "sources": sources
        })
    except Exception as e:
        return jsonify({"answer": f"Error: {str(e)}", "sources": []}), 500

if __name__ == "__main__":
    print("🚀 Starting CodeAtlas Flask Server on http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
