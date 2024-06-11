import logging
import os
import re

from slack_bolt import App, Say

from server.rag import rag_chain

logging.basicConfig(format="%(asctime)s %(message)s", level=logging.DEBUG)


def remove_mention(text: str) -> str:
    """メンションを除去する"""

    mention_regex = r"<@.*>"
    return re.sub(mention_regex, "", text).strip()


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

    result = rag_chain.invoke(payload)
    logger.debug(f"result: {result}")

    say(channel=channel, thread_ts=thread_ts, text=result)


app.start(port=int(os.environ.get("PORT", 3000)))
