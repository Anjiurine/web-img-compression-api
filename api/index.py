from http.server import BaseHTTPRequestHandler
import cv2
import numpy as np
import requests
import io
import os
from urllib.parse import unquote, urlparse, parse_qs
import json

class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        active_mode = os.environ.get("ACTIVE_MODE", "").lower() in ["true", "True"]

        if active_mode:
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            img_url = query_params.get('img', [''])[0]

            if not img_url:
                self.send_error_response(400, "Bad Request", "Missing 'img' query parameter")
                return

            img_url = unquote(img_url)
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.2088.76'}

            try:
                response = requests.get(img_url, stream=True, headers=headers)
                response.raise_for_status()
                image = cv2.imdecode(np.frombuffer(response.content, np.uint8), 1)
                _, ext = os.path.splitext(img_url)

                ext = ext.lower()

                encode_param, img_type = self.get_encode_param_and_type(ext)

                output = io.BytesIO()
                result, data = cv2.imencode(ext, image, encode_param)
                output.write(data)
                output.seek(0)
                self.send_response(200)
                self.send_header('Content-type', img_type)
                self.end_headers()
                self.wfile.write(output.read())

            except requests.exceptions.HTTPError as e:
                self.send_error_response(400, "Bad Request", str(e))

            except Exception as e:
                self.send_error_response(500, "Internal Server Error", str(e))
        else:
            self.send_error_response(400, "Bad Request", "Inactive mode is not supported")

    def send_error_response(self, status_code, error_type, message):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        error_response = {
            "error": {
                "type": error_type,
                "message": message
            }
        }
        self.wfile.write(json.dumps(error_response).encode('utf-8'))

    def get_encode_param_and_type(self, ext):
        if ext in [".jpg", ".jpeg"]:
            env_jpg_quality = int(os.environ.get("JPG_QUALITY"))
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), env_jpg_quality]
            img_type = "image/jpeg"
        elif ext == ".webp":
            env_webp_quality = int(os.environ.get("WEBP_QUALITY"))
            encode_param = [int(cv2.IMWRITE_WEBP_QUALITY), env_webp_quality]
            img_type = "image/webp"
        elif ext == ".png":
            env_png_compression = int(os.environ.get("PNG_COMPRESSION"))
            encode_param = [int(cv2.IMWRITE_PNG_COMPRESSION), env_png_compression]
            img_type = "image/png"
        else:
            raise ValueError("Unsupported image format")
        return encode_param, img_type
