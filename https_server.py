# https_server.py
import http.server
import ssl

# Server settings
PORT = 4443
SERVER_ADDRESS = ("localhost", PORT)

class SecureHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h1> Local HTTPS Server Running</h1>")

# Create server
httpd = http.server.HTTPServer(SERVER_ADDRESS, SecureHTTPRequestHandler)
httpd.socket = ssl.wrap_socket(httpd.socket, keyfile="key.pem", certfile="cert.pem", server_side=True)

print(f"🚀 HTTPS Server running at https://localhost:{PORT}")
httpd.serve_forever()
