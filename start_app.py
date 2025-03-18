import subprocess
import sys
import os
import time
import socket

def is_port_in_use(port):
    """Check if port is in use by trying to bind to it"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('localhost', port))
            return False
        except OSError:
            return True

def main():
    # Check if API server port is available
    api_port = 8000
    
    # If port is in use, we'll assume it's available to connect to
    port_in_use = is_port_in_use(api_port)
    api_server = None
    
    # Only start API server if port is not in use
    if not port_in_use:
        # Start the API server
        try:
            api_server = subprocess.Popen([sys.executable, 'api_server.py'])
            print(f"Started API server on port {api_port}")
            
            # Wait for the API server to start
            time.sleep(2)
        except Exception as e:
            print(f"Error starting API server: {str(e)}")
            print("Continuing without API server...")
    else:
        print(f"Port {api_port} is already in use, assuming API server is running")
    
    try:
        # Start the main application
        main_app = subprocess.Popen([sys.executable, 'script.py'])
        print("Started main application")
        
        # Wait for the main application to finish
        main_app.wait()
    finally:
        # Clean up the API server if we started it
        if api_server:
            api_server.terminate()
            try:
                api_server.wait(timeout=5)  # Wait up to 5 seconds
            except subprocess.TimeoutExpired:
                api_server.kill()  # Force kill if it won't terminate
            print("Cleaned up API server process")

if __name__ == "__main__":
    main() 