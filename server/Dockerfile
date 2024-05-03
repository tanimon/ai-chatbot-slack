FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml poetry.lock ./

RUN pip install poetry==1.8.2 \
    && poetry export -f requirements.txt --output requirements.txt \
    && pip uninstall -y poetry

RUN pip install --no-cache-dir -r requirements.txt

COPY app.py  ./

EXPOSE 3000

CMD [ "python", "-m", "app"]
