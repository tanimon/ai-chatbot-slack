import logging
import os
import re
from typing import Any

from slack_bolt import App, Say
from slack_bolt.adapter.aws_lambda import SlackRequestHandler

from server.rag import llm_chain, rag_chain

# ボットトークンと署名シークレットを使ってアプリを初期化する
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
    process_before_response=True,
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


SlackRequestHandler.clear_all_log_handlers()
logging.basicConfig(format="%(asctime)s %(message)s", level=logging.DEBUG)
logger = logging.getLogger()


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    logger.info(f"Received event: {event}")

    # Lambada関数でSlack Boltアプリを実行するためのアダプター
    # ref: https://github.com/slackapi/bolt-python/tree/main/examples/aws_lambda
    slack_handler = SlackRequestHandler(app=app)
    return slack_handler.handle(event, context)
