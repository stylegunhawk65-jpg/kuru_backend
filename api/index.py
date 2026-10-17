"""Vercel Serverless Function entry point for FastAPI backend."""

import os
import sys

# Ensure project root is in sys.path for serverless runtime
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Ensure serverless environment is explicitly signaled
os.environ["VERCEL"] = "1"

try:
    from app.main import app
except Exception as exc:
    import traceback
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    app = FastAPI(title="Kuru Backend - Serverless Diagnostic")

    err_msg = str(exc)
    tb_lines = traceback.format_exc().splitlines()

    @app.get("/{path:path}")
    async def catch_all_error(path: str = ""):
        return JSONResponse(
            status_code=500,
            content={
                "error": "Serverless Startup Diagnostic",
                "message": err_msg,
                "traceback": tb_lines[-15:],
            },
        )
