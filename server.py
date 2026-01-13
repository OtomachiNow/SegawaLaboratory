import http.server
import socketserver
import os
import time
import threading
import sys

# 設定
PORT = 8000
WATCH_DIR = os.path.join(os.getcwd(), 'posts')

# 最後に変更された時刻
last_modified_time = time.time()

def get_latest_mtime(directory):
    """指定ディレクトリ以下の最新の更新時刻を取得"""
    mtime = 0
    for root, dirs, files in os.walk(directory):
        for file in files:
            try:
                path = os.path.join(root, file)
                t = os.path.getmtime(path)
                if t > mtime:
                    mtime = t
            except:
                pass
    return mtime

def file_watcher():
    """ファイルの変更を監視するスレッド"""
    global last_modified_time
    while True:
        current_mtime = get_latest_mtime(WATCH_DIR)
        if current_mtime > last_modified_time:
            last_modified_time = current_mtime
        time.sleep(0.1) # 0.5 -> 0.1 に高速化

class LiveReloadHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # 監視用エンドポイント
        if self.path == '/_livereload/events':
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            
            # クライアントに接続を維持してもらう
            current_client_time = last_modified_time
            while True:
                if last_modified_time > current_client_time:
                    try:
                        self.wfile.write(b"data: reload\n\n")
                        self.wfile.flush()
                        current_client_time = last_modified_time
                    except:
                        break
                time.sleep(0.5)
            return

        # HTMLファイルへのリクエストなら、自動リロードJSを注入して返す
        if self.path.endswith('.html') or self.path.endswith('/'):
            try:
                # ファイルを読み込む
                f = self.send_head()
                if f:
                    content = f.read()
                    f.close()
                    
                    # 注入するスクリプト
                    script = b"""
                    <script>
                        // LiveReload Script
                        const evtSource = new EventSource("/_livereload/events");
                        evtSource.onmessage = function(event) {
                            if (event.data === "reload") {
                                console.log("File changed. Reloading...");
                                location.reload();
                            }
                        };
                    </script>
                    </body>
                    """
                    # </body> の直前に挿入
                    content = content.replace(b'</body>', script)
                    
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.send_header("Content-Length", str(len(content)))
                    self.end_headers()
                    self.wfile.write(content)
                    return
            except:
                pass
        
        # それ以外は通常通り
        super().do_GET()

if __name__ == "__main__":
    # 監視スレッド開始
    threading.Thread(target=file_watcher, daemon=True).start()
    
    print(f"Starting LiveReload server at http://localhost:{PORT}")
    print(f"Watching directory: {WATCH_DIR}")
    
    with socketserver.TCPServer(("", PORT), LiveReloadHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
