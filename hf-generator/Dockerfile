
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends fonts-dejavu-core libgomp1 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir --timeout=120 --retries=5 --trusted-host pypi.org --trusted-host files.pythonhosted.org fastapi uvicorn requests pillow pydantic scipy
RUN pip install --no-cache-dir --timeout=120 --retries=5 --trusted-host pypi.org --trusted-host files.pythonhosted.org onnxruntime
RUN pip install --no-cache-dir --timeout=120 --retries=5 --trusted-host pypi.org --trusted-host files.pythonhosted.org rembg
COPY logo.png /app/logo.png
COPY app.py /app/app.py
COPY fonts/ /app/fonts/
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
 