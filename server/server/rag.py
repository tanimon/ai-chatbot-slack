import os

import boto3
from langchain import hub
from langchain_aws import BedrockEmbeddings
from langchain_aws.chat_models import ChatBedrock
from langchain_community.vectorstores import OpenSearchVectorSearch
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable, RunnablePassthrough
from opensearchpy import RequestsHttpConnection
from requests_aws4auth import AWS4Auth  # type: ignore

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

llm_chain: Runnable = llm | StrOutputParser()
