FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir --timeout=120 --retries=5 --trusted-host pypi.org --trusted-host files.pythonhosted.org fastapi uvicorn requests beautifulsoup4 lxml pydantic
COPY app.py /app/app.py
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
