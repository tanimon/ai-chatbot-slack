import os
import re

from slack_bolt import App

# ボットトークンと署名シークレットを使ってアプリを初期化する
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
    process_before_response=True,
)


# ボットへのメンションに対するイベントリスナー
@app.event("app_mention")
def echo(event, say):
    print(f"app_mention event: {event}")

    text = event["text"]
    channel = event["channel"]
    thread_ts = event["ts"]

    # メンションを除去
    mention_regex = r"<@.*>"
    payload = re.sub(mention_regex, "", text).strip()
    print(f"payload: {payload}")

    answer = f"You mentioned to me:\n```{payload}```"

    say(channel=channel, thread_ts=thread_ts, text=answer)


app.start(port=int(os.environ.get("PORT", 3000)))
