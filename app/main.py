# app.py
from fastapi import FastAPI
from fastapi.responses import FileResponse
from api.v1 import tasks
from schemas.rules import LoggingMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
app = FastAPI(title="Video Creator TheTa API")
# Thêm route vào app
@app.get("/")
def read_root():
    return {"message": "Welcome to the TheTa Universe API endpoint!"}
# Add logging middleware
app.add_middleware(LoggingMiddleware)

# Register API routes
app.include_router(tasks.router)

# Static mounts
app.mount("/database", StaticFiles(directory="database"), name="database")

# Ensure absolute path for test-interface (since working dir may be app/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
UI_DIR = PROJECT_ROOT / "test-interface"
if UI_DIR.exists():
    app.mount("/ui", StaticFiles(directory=str(UI_DIR)), name="ui")

# Mount debug interface
DEBUG_INTERFACE = PROJECT_ROOT / "debug-interface.html"
if DEBUG_INTERFACE.exists():
    @app.get("/debug")
    async def get_debug_interface():
        return FileResponse(str(DEBUG_INTERFACE))