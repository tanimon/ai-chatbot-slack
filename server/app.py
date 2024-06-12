import logging
import os
import re

from slack_bolt import App, Say

from server.rag import llm_chain, rag_chain

logging.basicConfig(format="%(asctime)s %(message)s", level=logging.DEBUG)

# ボットトークンと署名シークレットを使ってアプリを初期化する
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
)

# ボットへのメンションに対するイベントリスナー
@app.event("app_mention")
def handle_app_mention(event, say: Say, logger: logging.Logger):
    logger.debug(f"app_mention event: {event}")

    text = event["text"]
    channel = event["channel"]
    thread_ts = event.get("thread_ts") or event["ts"]

    say(channel=channel, thread_ts=thread_ts, text="考え中です...少々お待ちください...")

    payload = remove_mention(text)
    logger.debug(f"payload: {payload}")

    result = (
        rag_chain.invoke(payload) if is_rag_enabled() else llm_chain.invoke(payload)
    )
    logger.debug(f"result: {result}")

    say(channel=channel, thread_ts=thread_ts, text=result)

@app.error
def handle_error(error, event, say: Say, logger: logging.Logger):
    logger.exception(f"エラーが発生しました: {error}")

    channel = event["channel"]
    thread_ts = event.get("thread_ts") or event["ts"]
    say(channel=channel, thread_ts=thread_ts, text=f"エラーが発生しました: {error}")


def remove_mention(text: str) -> str:
    """メンションを除去する"""

    mention_regex = r"<@.*>"
    return re.sub(mention_regex, "", text).strip()


def is_rag_enabled() -> bool:
    """RAGが有効かどうかを返す"""

    return os.environ.get("RAG_ENABLED", "false").lower() == "true"


app.start(port=int(os.environ.get("PORT", 3000)))
