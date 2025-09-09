 
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from core.config import SERVER_HOST
from pathlib import Path
import logging
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Log request
        logging.info(f"Request: {request.method} {request.url}")
        
        # Log request body if POST
        if request.method == "POST":
            body = await request.body()
            if body:
                try:
                    body_json = json.loads(body)
                    logging.info(f"Request body: {json.dumps(body_json, indent=2)}")
                except:
                    logging.info(f"Request body: {body}")

        response = await call_next(request)
        
        # Log response
        logging.info(f"Response status: {response.status_code}")
        return response


class DataReturn:
    @staticmethod
    def server_url(data_path: str) -> str:
        BASE_DIR = Path(__file__).resolve().parent.parent  # Đảm bảo trỏ đến thư mục gốc project
        STATIC_DIR = (BASE_DIR / "database").resolve()

        data_path = Path(data_path).resolve()
        try:
            relative_path = data_path.relative_to(STATIC_DIR)
        except ValueError:
            raise ValueError(f"{data_path} is not under static directory {STATIC_DIR}")

        return f"{SERVER_HOST}/database/{relative_path.as_posix()}"