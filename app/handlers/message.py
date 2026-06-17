import asyncio
import re
import uuid
from pathlib import Path
from urllib.parse import parse_qs

from linebot.v3.webhooks import (
    FileMessageContent,
    MessageEvent,
    PostbackEvent,
    TextMessageContent,
)

from globalVars import LINE_CHANNEL_ACCESS_TOKEN, UPLOAD_DIR
from line_client import LineClient
from services.contract_review_service import (
    REVIEW_TYPES,
    analyze_contract,
    get_review_label,
)
from utility.logHandler import PROJECT_LOGGER as LOGGER

ABOUT_TEXT = """您好，這是法務分身官方帳號。運用 AI 技術自動解析合約結構，智能識別缺漏條款、附件完整性與修改紀錄狀態，將傳統需數小時的人工審查壓縮至數分鐘。系統依據標準審查框架（封面摘要、合約主文、附件規格、追蹤修訂），即時標註高中低風險項目並產出結構化審查報告。目標是協助法務團隊聚焦關鍵風險，大幅提升合約審查效率與一致性。"""

WAITING_UPLOAD_MESSAGE = "請上傳欲進行 {review_label} 的 Word 檔案"
ANALYZING_MESSAGE = "法務分身正在幫您分析，預計需要 1~2 分鐘，請稍候片刻..."

# Temporary in-memory state for ngrok/local testing.
# TODO: Replace with Redis or database storage for multi-process production deploys.
_pending_review_by_target: dict[str, str] = {}


def _get_target_id(event: MessageEvent | PostbackEvent) -> str | None:
    source = getattr(event, "source", None)
    return getattr(source, "user_id", None) or getattr(source, "group_id", None)


def _sanitize_filename(filename: str) -> str:
    name = Path(filename or "uploaded_contract.docx").name
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)


def _is_word_file(filename: str) -> bool:
    return Path(filename.lower()).suffix in {".doc", ".docx", ".docm"}


async def handle_postback(event: PostbackEvent) -> None:
    data = parse_qs(event.postback.data or "")
    if data.get("action", [""])[0] != "contract_review":
        return

    review_type = data.get("type", [""])[0]
    await _select_contract_review(event, review_type)


async def handle_message(event: MessageEvent) -> None:
    message = event.message
    if isinstance(message, TextMessageContent):
        await _handle_text(event, message.text.strip())
    elif isinstance(message, FileMessageContent):
        await _handle_file(event, message)


async def _handle_text(event: MessageEvent, text: str) -> None:
    if not event.reply_token:
        return

    if text == "合約審核":
        async with LineClient(LINE_CHANNEL_ACCESS_TOKEN) as client:
            await client.reply(
                event.reply_token,
                [LineClient.build_contract_review_carousel()],
            )
        return

    if text in {"收文登記", "初審", "初審【業務/採購自審】", "法務審查"}:
        review_type = {
            "收文登記": "receipt",
            "初審": "initial_review",
            "初審【業務/採購自審】": "initial_review",
            "法務審查": "legal_review",
        }[text]
        await _select_contract_review(event, review_type)
        return

    if text == "關於":
        async with LineClient(LINE_CHANNEL_ACCESS_TOKEN) as client:
            await client.reply(event.reply_token, [LineClient.build_text(ABOUT_TEXT)])
        return

    if text == "訂閱":
        async with LineClient(LINE_CHANNEL_ACCESS_TOKEN) as client:
            await client.reply(
                event.reply_token,
                [LineClient.build_text("訂閱功能建置中。")],
            )


async def _select_contract_review(
    event: MessageEvent | PostbackEvent,
    review_type: str,
) -> None:
    if review_type not in REVIEW_TYPES or not event.reply_token:
        return

    target_id = _get_target_id(event)
    if not target_id:
        return

    _pending_review_by_target[target_id] = review_type
    review_label = get_review_label(review_type)

    async with LineClient(LINE_CHANNEL_ACCESS_TOKEN) as client:
        await client.reply(
            event.reply_token,
            [LineClient.build_text(WAITING_UPLOAD_MESSAGE.format(review_label=review_label))],
        )

    LOGGER.info("[_select_contract_review] target=%s review_type=%s", target_id, review_type)


async def _handle_file(event: MessageEvent, message: FileMessageContent) -> None:
    if not event.reply_token:
        return

    target_id = _get_target_id(event)
    if not target_id:
        return

    review_type = _pending_review_by_target.get(target_id)
    if not review_type:
        async with LineClient(LINE_CHANNEL_ACCESS_TOKEN) as client:
            await client.reply(
                event.reply_token,
                [LineClient.build_text("請先從選單選擇合約審核項目，再上傳 Word 檔案。")],
            )
        return

    original_filename = message.file_name or "uploaded_contract.docx"
    if not _is_word_file(original_filename):
        async with LineClient(LINE_CHANNEL_ACCESS_TOKEN) as client:
            await client.reply(
                event.reply_token,
                [LineClient.build_text("請上傳 Word 檔案（.doc、.docx 或 .docm）。")],
            )
        return

    async with LineClient(LINE_CHANNEL_ACCESS_TOKEN) as client:
        content = await client.download_content(message.id)
        await client.reply(event.reply_token, [LineClient.build_text(ANALYZING_MESSAGE)])

    file_path = await _save_uploaded_file(content, original_filename, target_id)

    # This is the explicit handoff point from Line file receiving to contract analysis.
    # Change analyze_contract() when the real OpenAI + md prompt flow is ready.
    result = await analyze_contract(file_path=file_path, review_type=review_type)

    _pending_review_by_target.pop(target_id, None)

    async with LineClient(LINE_CHANNEL_ACCESS_TOKEN) as client:
        await client.push(target_id, [LineClient.build_text(result)])

    LOGGER.info(
        "[_handle_file] target=%s filename=%s saved=%s review_type=%s",
        target_id,
        original_filename,
        file_path,
        review_type,
    )


async def _save_uploaded_file(content: bytes, original_filename: str, target_id: str) -> Path:
    safe_filename = _sanitize_filename(original_filename)
    upload_path = UPLOAD_DIR / f"{target_id}_{uuid.uuid4().hex}_{safe_filename}"
    await asyncio.to_thread(upload_path.write_bytes, content)
    return upload_path
