FROM python:3.11-slim

WORKDIR /app

# System deps kept minimal; scikit-learn wheels are prebuilt.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt uvicorn fastapi

COPY . .

# Build the DB + RAG index at image build so first request is fast.
RUN python scripts/init_db.py || true

EXPOSE 8000
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
