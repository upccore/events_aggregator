FROM python:3.11-slim

RUN addgroup --system --gid 1000 appuser && \
    adduser --system --uid 1000 --ingroup appuser appuser

WORKDIR /app
COPY --chown=appuser:appuser . .

RUN pip install --no-cache-dir -r requirements.txt

USER appuser

EXPOSE 8000

CMD ["python", "app.py"]