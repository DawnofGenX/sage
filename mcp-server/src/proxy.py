"""Reverse proxy: routes /api/* and /mcp to the backend, everything else to the frontend."""
import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, StreamingResponse
import os

BACKEND = "http://localhost:8001"
FRONTEND = "http://localhost:3000"

app = FastAPI()

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy(request: Request):
    path = request.url.path
    
    # Backend routes
    if path.startswith("/api") or path.startswith("/mcp"):
        url = f"{BACKEND}{path}"
        body = await request.body()
        headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}
        
        async with httpx.AsyncClient() as client:
            resp = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                content=body,
                params=request.query_params,
            )
        
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            headers=dict(resp.headers),
            media_type=resp.headers.get("content-type"),
        )
    
    # Frontend routes
    if path == "/" or not os.path.exists(f"/home/hermes/sage/mcp-server/static{path}"):
        # SPA fallback: serve index.html for client-side routes
        return FileResponse("/home/hermes/sage/mcp-server/static/index.html")
    
    # Static assets
    return FileResponse(f"/home/hermes/sage/mcp-server/static{path}")
