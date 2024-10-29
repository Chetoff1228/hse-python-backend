FROM python:3.12.6-slim
WORKDIR /app
RUN apt-get update && apt-get install -y curl build-essential

RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

COPY pyproject.toml poetry.lock /app/

RUN poetry install --no-root

COPY . /app

EXPOSE 8000
EXPOSE 8001

CMD ["poetry", "run", "uvicorn", "shop_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
