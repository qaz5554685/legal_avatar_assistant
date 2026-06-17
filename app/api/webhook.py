import asyncio

from linebot.v3 import WebhookParser
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import (
    FileMessageContent,
    MessageEvent,
    PostbackEvent,
    TextMessageContent,
)
from starlette.requests import Request
from starlette.responses import JSONResponse

from globalVars import LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET
from handlers.message import handle_message, handle_postback
from line_client import LineClient
from utility.logHandler import PROJECT_LOGGER as LOGGER


def _get_push_target(event) -> str | None:
    source = getattr(event, "source", None)
    return getattr(source, "user_id", None) or getattr(source, "group_id", None)


async def _route_event(event) -> None:
    try:
        match event:
            case PostbackEvent():
                await handle_postback(event)
            case MessageEvent(message=FileMessageContent()):
                await handle_message(event)
            case MessageEvent(message=TextMessageContent()):
                await handle_message(event)
            case _:
                LOGGER.info("[_route_event] Unhandled event type: %s", type(event).__name__)
    except Exception as exc:
        LOGGER.exception("[_route_event] Error handling event: %s", exc)
        target = _get_push_target(event)
        if target and LINE_CHANNEL_ACCESS_TOKEN:
            async with LineClient(LINE_CHANNEL_ACCESS_TOKEN) as client:
                await client.push(
                    target,
                    [LineClient.build_text("處理時發生錯誤，請稍後再試。")],
                )


async def line_webhook(request: Request) -> JSONResponse:
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET:
        LOGGER.error("[line_webhook] Missing LINE channel credentials")
        return JSONResponse({"error": "LINE channel credentials are not configured."}, status_code=500)

    body = await request.body()
    signature = request.headers.get("X-Line-Signature", "")

    try:
        parser = WebhookParser(LINE_CHANNEL_SECRET)
        events = parser.parse(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        LOGGER.warning("[line_webhook] Invalid Line signature")
        return JSONResponse({"error": "Forbidden."}, status_code=403)

    for event in events:
        asyncio.create_task(_route_event(event))

    return JSONResponse({"status": "ok"})
