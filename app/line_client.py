from linebot.v3.messaging import (
    AsyncApiClient,
    AsyncMessagingApi,
    AsyncMessagingApiBlob,
    Configuration,
    FlexMessage,
    FlexContainer,
    PushMessageRequest,
    ReplyMessageRequest,
    TextMessage,
)


class LineClient:
    def __init__(self, channel_access_token: str) -> None:
        config = Configuration(access_token=channel_access_token)
        self._api_client = AsyncApiClient(configuration=config)
        self._api = AsyncMessagingApi(self._api_client)
        self._blob = AsyncMessagingApiBlob(self._api_client)

    async def aclose(self) -> None:
        await self._api_client.close()

    async def __aenter__(self) -> "LineClient":
        return self

    async def __aexit__(self, *_) -> None:
        await self.aclose()

    @staticmethod
    def build_text(text: str) -> TextMessage:
        return TextMessage(text=text)

    @staticmethod
    def build_contract_review_carousel() -> FlexMessage:
        items = [
            {
                "key": "receipt",
                "title": "收文登記",
                "subtitle": "Contract Receipt & Registration",
                "description": (
                    "收文登記是合約審核流程的第一關，目的是確認合約文件的完整性與基本資訊，"
                    "建立可追蹤的審核紀錄，並分派至適當的後續審核人員。"
                ),
            },
            {
                "key": "initial_review",
                "title": "初審【業務/採購自審】",
                "subtitle": "Initial Review [Business/Procurement]",
                "description": (
                    "初審由業務或採購人員執行，確認合約內容與商業談判結果一致，"
                    "並透過 AI 輔助找出可能的風險條款。"
                ),
            },
            {
                "key": "legal_review",
                "title": "法務審查",
                "subtitle": "Legal Review",
                "description": (
                    "法務審查是合約審核的核心把關階段，由法務人員或委外法律顧問執行完整的條款實質審查。"
                ),
            },
        ]

        bubbles = []
        for item in items:
            bubbles.append(
                {
                    "type": "bubble",
                    "size": "mega",
                    "body": {
                        "type": "box",
                        "layout": "vertical",
                        "spacing": "md",
                        "contents": [
                            {
                                "type": "text",
                                "text": item["title"],
                                "weight": "bold",
                                "size": "lg",
                                "wrap": True,
                            },
                            {
                                "type": "text",
                                "text": item["subtitle"],
                                "size": "xs",
                                "color": "#666666",
                                "wrap": True,
                            },
                            {
                                "type": "text",
                                "text": item["description"],
                                "size": "sm",
                                "color": "#333333",
                                "wrap": True,
                            },
                        ],
                    },
                    "footer": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "button",
                                "style": "primary",
                                "action": {
                                    "type": "postback",
                                    "label": "選擇",
                                    "data": f"action=contract_review&type={item['key']}",
                                    "displayText": item["title"],
                                },
                            }
                        ],
                    },
                }
            )

        return FlexMessage(
            altText="合約審核",
            contents=FlexContainer.from_dict({"type": "carousel", "contents": bubbles}),
        )

    async def reply(self, reply_token: str, messages: list) -> None:
        await self._api.reply_message(
            ReplyMessageRequest(
                replyToken=reply_token,
                messages=messages[:5],
                notificationDisabled=False,
            )
        )

    async def push(self, to: str, messages: list) -> None:
        await self._api.push_message(
            PushMessageRequest(
                to=to,
                messages=messages[:5],
                notificationDisabled=False,
                customAggregationUnits=None,
            )
        )

    async def download_content(self, message_id: str) -> bytes:
        return await self._blob.get_message_content(message_id)
