from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
from typing import List, Dict, Any
import uvicorn
from fastapi.responses import HTMLResponse

app = FastAPI(title="ROI Analyzer API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active WebSocket connections
active_connections: List[WebSocket] = []

@app.get("/ws-test")
async def get_websocket_test():
    """Provide a test HTML page with WebSocket connection"""
    html = """
    <!DOCTYPE html>
    <html>
        <head>
            <title>ROI Analyzer WebSocket Test</title>
        </head>
        <body>
            <h1>ROI Analyzer WebSocket Test</h1>
            <p>Status: <span id="status">Disconnected</span></p>
            <button onclick="connect()">Connect</button>
            <button onclick="disconnect()">Disconnect</button>
            <div id="messages" style="height: 400px; overflow-y: scroll; border: 1px solid #ccc; margin-top: 20px; padding: 10px;"></div>
            
            <script>
                var ws = null;
                
                function connect() {
                    if (ws !== null) {
                        document.getElementById('status').innerText = 'Already connected';
                        return;
                    }
                    
                    // Use the correct websocket URL based on the current location
                    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
                    const wsUrl = protocol + '//' + location.host + '/ws';
                    
                    document.getElementById('status').innerText = 'Connecting...';
                    ws = new WebSocket(wsUrl);
                    
                    ws.onopen = function(event) {
                        document.getElementById('status').innerText = 'Connected';
                    };
                    
                    ws.onmessage = function(event) {
                        const messagesDiv = document.getElementById('messages');
                        const message = document.createElement('div');
                        message.style.borderBottom = '1px solid #eee';
                        message.style.padding = '5px 0';
                        
                        try {
                            const data = JSON.parse(event.data);
                            message.innerText = JSON.stringify(data, null, 2);
                        } catch (e) {
                            message.innerText = event.data;
                        }
                        
                        messagesDiv.appendChild(message);
                        messagesDiv.scrollTop = messagesDiv.scrollHeight;
                    };
                    
                    ws.onclose = function(event) {
                        document.getElementById('status').innerText = 'Disconnected';
                        ws = null;
                    };
                    
                    ws.onerror = function(event) {
                        document.getElementById('status').innerText = 'Error occurred';
                        console.error("WebSocket error:", event);
                    };
                }
                
                function disconnect() {
                    if (ws !== null) {
                        ws.close();
                        ws = null;
                        document.getElementById('status').innerText = 'Disconnected';
                    }
                }
            </script>
        </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        # Send initial connection message
        await websocket.send_json({"status": "connected", "message": "WebSocket connection established"})
        
        # Keep the connection alive and handle messages
        while True:
            try:
                # Receive and echo any messages (for testing)
                data = await websocket.receive_text()
                await websocket.send_text(f"You sent: {data}")
            except Exception as e:
                # Handle any errors in receiving messages
                print(f"Error receiving message: {str(e)}")
                break
    except Exception as e:
        print(f"WebSocket error: {str(e)}")
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)

async def broadcast_update(data: Dict[str, Any]):
    """Broadcast updates to all connected clients"""
    disconnected = []
    for i, connection in enumerate(active_connections):
        try:
            await connection.send_json(data)
        except Exception as e:
            print(f"Error sending to client {i}: {str(e)}")
            disconnected.append(connection)
    
    # Remove disconnected clients
    for connection in disconnected:
        if connection in active_connections:
            active_connections.remove(connection)

@app.post("/update")
async def update_data(data: Dict[str, Any]):
    """Endpoint to receive updates from the main application"""
    await broadcast_update(data)
    return {"status": "success", "clients": len(active_connections)}

@app.get("/")
async def root():
    """Root endpoint with API documentation"""
    return {
        "name": "ROI Analyzer API",
        "version": "1.0.0",
        "endpoints": {
            "websocket": "/ws",
            "websocket_test": "/ws-test",
            "update": "/update"
        },
        "documentation": "/docs"
    }

def start_server():
    """Start the FastAPI server"""
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    start_server() 