from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from api.webhook import line_webhook


async def health(_: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "legal_avatar_assistant"})


routes = [
    Route("/", health, methods=["GET"]),
    Route("/health", health, methods=["GET"]),
    Route("/line/webhook", line_webhook, methods=["POST"]),
]

app = Starlette(routes=routes)
