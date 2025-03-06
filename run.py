# run.py
import subprocess
import sys
import os
import webbrowser
from time import sleep
import platform
import socket
import threading

class ServiceManager:
    def __init__(self):
        self.os_type = platform.system().lower() # detect `daewin`(macos) or `windows`
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.append(self.base_dir) # base directory to Python path
        self.api_script = os.path.join(self.base_dir, 'src', 'api', 'main.py')
        self.web_dir = os.path.join(self.base_dir, 'src', 'web')
        self.logs_dir = os.path.join(self.base_dir, 'logs')
        
        # Set the path to the Python executable based on the OS
        if self.is_windows():
            self.venv_python = os.path.join(self.base_dir, 'venv', 'Scripts', 'python.exe')
        else:
            # For macOS/Linux
            self.venv_python = os.path.join(self.base_dir, 'venv', 'bin', 'python')
        
        # Create logs directory and set environment variable
        os.makedirs(self.logs_dir, exist_ok=True)
        os.environ['LOGS_DIR'] = self.logs_dir
        
        self.api_process = None
        self.http_process = None
        
    def is_windows(self):
        return self.os_type == 'windows'
    
    def is_port_in_use(self, port):
        """Check if a port is in use"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0
    
    def start_fastapi_server(self):
        """Start the FastAPI server"""
        print("[START] Starting FastAPI server...")

        # For Windows, we'll start the server in the same process
        if self.is_windows():
            try:
                # Start the server in a separate thread
                def run_server():
                    # Import here to avoid circular imports
                    from src.api.main import app
                    import uvicorn
                    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
                
                server_thread = threading.Thread(target=run_server)
                server_thread.daemon = True  # This ensures the thread will exit when the main program exits
                server_thread.start()
                
                # Wait for the server to start
                for i in range(10):  # Try 10 times
                    if self.is_port_in_use(8000):
                        print("[OK] FastAPI server is running on port 8000")
                        return server_thread
                    print(f"Waiting for server to start (attempt {i+1}/10)...")
                    sleep(1)
                
                print("[ERROR] FastAPI server failed to start")
                return None
            except Exception as e:
                print(f"[ERROR] Error starting FastAPI server: {str(e)}")
                return None
        else:
            # For macOS/Linux, use the original approach
            try:
                api_cmd = [self.venv_python, '-m', 'src.api.main']
                self.api_process = subprocess.Popen(
                    api_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Give the process a moment to start
                sleep(3)
                
                # Check if process is still running
                if self.api_process.poll() is not None:
                    stdout, stderr = self.api_process.communicate()
                    error_msg = stderr or stdout
                    print(f"❌ Error starting FastAPI server: {error_msg}")
                    return None
                
                return self.api_process
            except Exception as e:
                print(f"[ERROR] Error starting FastAPI server: {str(e)}")
                return None

    def kill_process_on_port(self, port):
        """Kill process using the specified port for both Windows and macOS/Linux"""
        try:
            if self.is_windows():
                # Windows command to kill process on port
                cmd = f"for /f \"tokens=5\" %a in ('netstat -aon ^| findstr :{port}') do taskkill /F /PID %a"
                subprocess.run(cmd, shell=True, stderr=subprocess.DEVNULL)
            else:
                # macOS/Linux command to kill process on port
                cmd = f"lsof -ti:{port} | xargs kill -9"
                subprocess.run(cmd, shell=True, stderr=subprocess.DEVNULL)
            print(f"Cleaned up port {port}")
            sleep(1)  # Give time for port to be released
        except Exception as e:
            print("[WARNING] Warning during port cleanup: {str(e)}")

    def verify_paths(self):
        """Verify that all required paths exist"""
        if not os.path.exists(self.api_script):
            print(f"[ERROR] Could not find API script at {self.api_script}")
            return False
        if not os.path.exists(self.web_dir):
            print(f"[ERROR] Could not find web directory at {self.web_dir}")
            return False
        return True

    def start_http_server(self):
        """Start the HTTP server"""
        print("[START] Starting HTTP server...")
        
        # For Windows, we'll use a different approach
        if self.is_windows():
            try:
                # Start a simple HTTP server in a separate thread
                def run_http_server():
                    import http.server
                    import socketserver
                    
                    handler = http.server.SimpleHTTPRequestHandler
                    with socketserver.TCPServer(("127.0.0.1", 3000), handler) as httpd:
                        print("[OK] HTTP server is running on port 3000")
                        httpd.serve_forever()
                
                http_thread = threading.Thread(target=run_http_server)
                http_thread.daemon = True
                http_thread.start()
                
                # Wait for the server to start
                for i in range(5):
                    if self.is_port_in_use(3000):
                        print("[OK] HTTP server is running on port 3000")
                        return http_thread
                    print(f"Waiting for HTTP server to start (attempt {i+1}/5)...")
                    sleep(1)
                
                print("[ERROR] HTTP server failed to start")
                return None
            except Exception as e:
                print(f"[ERROR] Error starting HTTP server: {str(e)}")
                return None
        else:
            # For macOS/Linux, use the original approach
            http_cmd = [self.venv_python, '-m', 'http.server', '3000', '--bind', '127.0.0.1']
            try:
                return subprocess.Popen(http_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except Exception as e:
                print(f"[ERROR] Error starting HTTP server: {str(e)}")
                return None

    def verify_server_running(self, port: int, max_retries: int = 5) -> bool:
        """Verify if a server is running on the specified port"""
        # For Windows, we'll use a simpler approach
        if self.is_windows():
            return self.is_port_in_use(port)
        
        # For macOS/Linux, use the original approach
        import requests
        from time import sleep
        
        for i in range(max_retries):
            try:
                if port == 8000:
                    response = requests.get(f"http://localhost:{port}/health", timeout=5)
                    if response.status_code == 200:
                        print(f"✅ Server on port {port} is running")
                        return True
                elif port == 3000:
                    response = requests.get(f"http://localhost:{port}", timeout=5)
                    if response.status_code in [200, 304]:
                        print(f"✅ Server on port {port} is running")
                        return True
            except requests.exceptions.ConnectionError:
                print(f"Waiting for server on port {port} (attempt {i+1}/{max_retries})...")
                sleep(3)
            except requests.exceptions.Timeout:
                print(f"Timeout waiting for server on port {port} (attempt {i+1}/{max_retries})...")
                sleep(3)

        print(f"❌ Server failed to start on port {port} after {max_retries} attempts")
        return False

    def run_services(self):
        """Main method to run all services"""
        api_process = None
        http_process = None
        
        try:
            # Create necessary directories
            os.makedirs(self.logs_dir, exist_ok=True)

            # Verify paths
            if not self.verify_paths():
                return

            # Clean up existing processes if needed
            if self.is_windows():
                response = input("Do you want to clean up existing processes on port 8000 and 3000? (y/n): ")
                if response.lower() == 'y':
                    self.kill_process_on_port(8000)
                    self.kill_process_on_port(3000)
                    sleep(2)  # Give more time for ports to be released
            else:
                # For Linux/WSL, just try to clean up without asking
                self.kill_process_on_port(8000)
                self.kill_process_on_port(3000)
                sleep(2)

            # Start FastAPI server
            api_process = self.start_fastapi_server()
            if api_process is None:
                print("[ERROR] Failed to start FastAPI server")
                return
            print("[OK] FastAPI server started")

            # Start HTTP server
            original_dir = os.getcwd()
            os.chdir(self.web_dir)
            http_process = self.start_http_server()
            if http_process is None:
                print("[ERROR] Failed to start HTTP server")
                os.chdir(original_dir)
                return
            print("[OK] HTTP server started")
            
            # Wait a moment before opening browser
            sleep(2)

            # Open browser (only in Windows)
            if self.is_windows():
                webbrowser.open('http://localhost:3000')
                print("[OK] Browser opened")

            # Print access information
            print("\n[OK] All services are running!")
            print("[INFO] API URL: http://localhost:8000")
            print("[INFO] Web Interface: http://localhost:3000")
            print("\n[INFO] Press Ctrl+C to stop all services...")

            # Keep the main thread running without using input()
            try:
                while True:
                    sleep(1)
                    # Check if processes are still running
                    if not self.is_windows():
                        if api_process and api_process.poll() is not None:
                            print("[ERROR] FastAPI server stopped unexpectedly")
                            break
                        if http_process and http_process.poll() is not None:
                            print("[ERROR] HTTP server stopped unexpectedly")
                            break
            except KeyboardInterrupt:
                print("\n[INFO] Stopping services (Ctrl+C pressed)...")
            
        except Exception as e:
            print(f"[ERROR] {str(e)}")
        finally:
            # Cleanup
            try:
                if self.is_windows():
                    self.kill_process_on_port(8000)
                    self.kill_process_on_port(3000)
                else:
                    # For Linux/WSL, use process termination
                    if isinstance(api_process, subprocess.Popen):
                        api_process.terminate()
                        api_process.wait(timeout=5)  # Wait for process to terminate
                    if isinstance(http_process, subprocess.Popen):
                        http_process.terminate()
                        http_process.wait(timeout=5)  # Wait for process to terminate
                    # Force kill if processes are still running
                    self.kill_process_on_port(8000)
                    self.kill_process_on_port(3000)
                print("[OK] Cleanup completed")
            except Exception as e:
                print(f"[WARNING] Error during cleanup: {str(e)}")
                # Try force kill as last resort
                self.kill_process_on_port(8000)
                self.kill_process_on_port(3000)

def main():
    print(f"🖥️  Operating System: {platform.system()}")
    manager = ServiceManager()
    manager.run_services()

if __name__ == "__main__":
    main()