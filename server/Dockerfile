FROM public.ecr.aws/lambda/python:3.12

WORKDIR ${LAMBDA_TASK_ROOT}

RUN pip install poetry==1.8.2

COPY pyproject.toml poetry.lock ./

RUN poetry export -f requirements.txt --output requirements.txt \
    && pip uninstall -y poetry \
    && pip install --no-cache-dir -r requirements.txt

COPY server ./server/
COPY slack_bot_handler.py ./

CMD ["slack_bot_handler.handler"]
