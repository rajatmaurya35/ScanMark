from http.server import BaseHTTPRequestHandler
from app import app

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        with app.test_client() as test_client:
            response = test_client.get(self.path)
            self.wfile.write(response.data)
        return

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        with app.test_client() as test_client:
            response = test_client.post(self.path, data=post_data)
            self.wfile.write(response.data)
        return
