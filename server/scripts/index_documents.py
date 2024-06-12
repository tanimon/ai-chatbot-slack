import os

import boto3
from dotenv import load_dotenv
from langchain_aws import BedrockEmbeddings
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import OpenSearchVectorSearch
from langchain_text_splitters import RecursiveCharacterTextSplitter
from opensearchpy import RequestsHttpConnection
from requests_aws4auth import AWS4Auth  # type: ignore

load_dotenv()

print("Loading started...")

loader = WebBaseLoader(
    web_paths=["https://classmethod.jp/services/generative-ai/ai-starter/"]
)
docs = loader.load()

print("Loading completed!")


print("Splitting started...")

text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
splits = text_splitter.split_documents(docs)
embedding = BedrockEmbeddings(
    model_id="amazon.titan-embed-text-v2:0", region_name="us-east-1", client=None
)

print("Splitting completed!")


print("Indexing started...")

credentials = boto3.Session().get_credentials()
aws_auth = AWS4Auth(
    refreshable_credentials=credentials,
    region="ap-northeast-1",
    service="aoss",
)

vectorstore = OpenSearchVectorSearch.from_documents(
    documents=splits,
    embedding=embedding,
    opensearch_url=os.environ["AOSS_ENDPOINT_URL"],
    index_name=os.environ["AOSS_INDEX_NAME"],
    http_auth=aws_auth,
    timeout=300,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    engine="faiss",
)

print("Indexing completed!")
