# NOTE: Python v3.12.4を利用するとlangchainをインポートする際にエラーが発生するため、v3.12.3を利用する
# ref: https://stackoverflow.com/questions/78593700/langchain-community-langchain-packages-giving-error-missing-1-required-keywor
FROM python:3.12.3-slim

WORKDIR /app

RUN pip install poetry==1.8.2

COPY pyproject.toml poetry.lock ./

RUN poetry export -f requirements.txt --output requirements.txt \
    && pip uninstall -y poetry \
    && pip install --no-cache-dir -r requirements.txt

COPY server ./server/
COPY app.py ./

EXPOSE 3000

CMD [ "python", "-m", "app"]
