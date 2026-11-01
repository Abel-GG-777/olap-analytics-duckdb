FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080 DUCKDB_PATH=/srv/data/retail.duckdb
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
RUN python -m app.warehouse --path /srv/data/retail.duckdb && useradd --uid 10001 --create-home runner && chown -R runner:runner /srv
USER runner
EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1"]
