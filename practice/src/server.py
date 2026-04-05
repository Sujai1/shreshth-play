"""A simple HTTP server for serving model predictions."""
import json
from http.server import HTTPServer, BaseHTTPRequestHandler


# Simulated model
MODEL_WEIGHT = 0.5
MODEL_BIAS = 0.3


class PredictionHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())

        elif self.path == "/model-info":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            info = {"weight": MODEL_WEIGHT, "bias": MODEL_BIAS, "version": "1.0"}
            self.wfile.write(json.dumps(info).encode())

        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "not found"}).encode())

    def do_POST(self):
        if self.path == "/predict":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body)
                x = data["input"]
                prediction = MODEL_WEIGHT * x + MODEL_BIAS
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"input": x, "prediction": prediction}).encode())
            except (json.JSONDecodeError, KeyError) as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {format % args}")


def main():
    port = 8080
    server = HTTPServer(("localhost", port), PredictionHandler)
    print(f"Server running on http://localhost:{port}")
    print("Endpoints: GET /health, GET /model-info, POST /predict")
    print("Press Ctrl+C to stop")
    server.serve_forever()


if __name__ == "__main__":
    main()
