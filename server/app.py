import logging
import os
import re

import slack_sdk
from interpreter import interpreter
from slack_bolt import App

logging.basicConfig(format="%(asctime)s %(message)s", level=logging.DEBUG)


# Open InterpreterがBedrock経由でLlama3モデルを利用するように設定
interpreter.llm.model = "bedrock/meta.llama3-70b-instruct-v1:0"
interpreter.llm.context_window = 8000  # type: ignore

# LLMが生成したコードを自動実行するように設定
# 実行すべきでないコードが生成される可能性もあるので、この設定を利用する際は注意が必要
interpreter.auto_run = True

# Open Interpreterでus-east-1のBedrock APIが利用されるように設定
os.environ["AWS_REGION_NAME"] = "us-east-1"


def chat(message):
    for chunk in interpreter.chat(message, display=True, stream=True):  # type: ignore
        logging.info(f"chunk: {chunk}")
        yield chunk


def remove_mention(text):
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
def handle_app_mention(event, say, client: slack_sdk.WebClient):
    print(f"app_mention event: {event}")

    text = event["text"]
    channel = event["channel"]
    thread_ts = event.get("thread_ts") or event["ts"]

    response = say(
        channel=channel, thread_ts=thread_ts, text="考え中です...少々お待ちください..."
    )

    payload = remove_mention(text)
    print(f"payload: {payload}")

    text = ""
    prev_text_length = 0

    try:
        for chunk in chat(payload):
            content = chunk.get("content")
            print(f"content: {content}")

            if not content:
                continue

            text += str(content)

            # `msg_too_long` エラー抑制のため、2000文字を超えたら新しいメッセージとして送信する
            if len(text) > 2000:
                text = str(content)
                prev_text_length = len(text)
                response = client.chat_postMessage(
                    channel=channel, thread_ts=thread_ts, text=text
                )

            # 20文字ごとに既存のメッセージを更新することで、Streaming形式で表示させる
            elif len(text) - prev_text_length > 20:
                client.chat_update(
                    channel=channel,
                    ts=response["ts"],
                    text=text,
                )
                prev_text_length = len(text)

        # ループ完了後、未送信の内容が残っていればメッセージを更新
        if len(text) > prev_text_length:
            client.chat_update(
                channel=channel,
                ts=response["ts"],
                text=text,
            )
    except Exception as e:
        logging.error(
            "エラー",
            e,
            e.__cause__,
            e.__class__,
        )
        say(channel=channel, thread_ts=thread_ts, text=f"エラーが発生しました: {e}")


app.start(port=int(os.environ.get("PORT", 3000)))
