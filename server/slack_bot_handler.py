import logging
import os
import re
from typing import Any, Callable, Sequence

from slack_bolt import App, BoltRequest, Say
from slack_bolt.adapter.aws_lambda import SlackRequestHandler

from server.rag import llm_chain, rag_chain

SlackRequestHandler.clear_all_log_handlers()  # NOTE: このメソッド呼び出し以前に記述されたlogger呼び出しはログ出力されない模様
logging.basicConfig(format="%(asctime)s %(message)s", level=logging.DEBUG)
logger = logging.getLogger()

# ボットトークンと署名シークレットを使ってアプリを初期化する
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
    process_before_response=True,
)


# タイムアウトによるリトライをスキップするためのミドルウェア
@app.middleware
def skip_timeout_retry(
    request: BoltRequest, next: Callable[[], None], logger: logging.Logger
):
    logger.debug(f"request.headers: {request.headers}")

    retry_num = request.headers.get("x-slack-retry-num", [])
    retry_reason = request.headers.get("x-slack-retry-reason", [])
    logger.debug(f"retry_num: {retry_num}, retry_reason: {retry_reason}")

    if is_timeout_retry(retry_num=retry_num, retry_reason=retry_reason):
        logger.info("Skip retry request")
        return

    logger.info("Continue to the next middleware")
    next()


def is_timeout_retry(*, retry_num: Sequence[str], retry_reason: Sequence[str]) -> bool:
    if retry_num == []:
        return False

    # 本来は"http_timeout"のみをチェックすべきだが、正常にレスポンスされた場合でもリトライ理由が"http_error"になることがあるため、両方をチェックする
    if retry_reason == ["http_timeout"] or retry_reason == ["http_error"]:
        return True

    return False


# ボットへのメンションに対するイベントリスナー
def handle_app_mention(event, say: Say, logger: logging.Logger):
    logger.debug(f"app_mention event: {event}")

    text = event["text"]
    channel = event["channel"]
    thread_ts = event.get("thread_ts") or event["ts"]

    say(channel=channel, thread_ts=thread_ts, text="考え中です...少々お待ちください...")

    payload = remove_mention(text)
    logger.debug(f"payload: {payload}")

    try:
        result = (
            rag_chain.invoke(payload) if is_rag_enabled() else llm_chain.invoke(payload)
        )
        logger.debug(f"result: {result}")

        say(channel=channel, thread_ts=thread_ts, text=result)
    except Exception as e:
        logger.exception("エラーが発生しました")
        say(channel=channel, thread_ts=thread_ts, text=f"エラーが発生しました: {e}")


def remove_mention(text: str) -> str:
    """メンションを除去する"""

    mention_regex = r"<@.*>"
    return re.sub(mention_regex, "", text).strip()


def is_rag_enabled() -> bool:
    """RAGが有効かどうかを返す"""

    return os.environ.get("RAG_ENABLED", "false").lower() == "true"


def noop_ack():
    pass


# 3秒以内にレスポンスを返さないとリトライが発生してしまうため、それを防ぐためにLazyリスナーとして登録する
# この対応を行っても、コールドスタート時には3秒を超えてしまうようでリトライが発生する
# ref:
# - https://api.slack.com/apis/events-api#retries
# - https://slack.dev/bolt-python/ja-jp/concepts#lazy-listeners
# - https://github.com/slackapi/bolt-python/issues/678#issuecomment-1171837818
app.event("app_mention")(ack=noop_ack, lazy=[handle_app_mention])


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    logger.info(f"Received event: {event}")

    # Lambada関数でSlack Boltアプリを実行するためのアダプター
    # ref: https://github.com/slackapi/bolt-python/tree/main/examples/aws_lambda
    slack_handler = SlackRequestHandler(app=app)
    return slack_handler.handle(event, context)
