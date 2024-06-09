import logging
import os
import re

import boto3
import slack_sdk
from langchain import hub
from langchain_aws import BedrockEmbeddings
from langchain_aws.chat_models import ChatBedrock
from langchain_community.vectorstores import OpenSearchVectorSearch
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable, RunnablePassthrough
from opensearchpy import RequestsHttpConnection
from requests_aws4auth import AWS4Auth  # type: ignore
from slack_bolt import App

logging.basicConfig(format="%(asctime)s %(message)s", level=logging.DEBUG)
logger = logging.getLogger(__name__)

embedding = BedrockEmbeddings(
    model_id="amazon.titan-embed-text-v2:0", region_name="us-east-1", client=None
)

credentials = boto3.Session().get_credentials()
aws_auth = AWS4Auth(
    refreshable_credentials=credentials,
    region="ap-northeast-1",
    service="aoss",
)

vectorstore = OpenSearchVectorSearch(
    opensearch_url=os.environ["AOSS_ENDPOINT_URL"],
    index_name=os.environ["AOSS_INDEX_NAME"],
    embedding_function=embedding,
    http_auth=aws_auth,
    timeout=300,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    engine="faiss",
)

retriever = vectorstore.as_retriever()


def format_docs(docs: list[Document]) -> str:
    return "\n\n".join([doc.page_content for doc in docs])


prompt = hub.pull("rlm/rag-prompt")

llm = ChatBedrock(
    model_id="anthropic.claude-3-haiku-20240307-v1:0",
    region_name="us-east-1",
    client=None,
)

rag_chain: Runnable = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)


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
def handle_app_mention(event, say, client: slack_sdk.WebClient):
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
