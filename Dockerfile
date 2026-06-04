FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY bill_advisor/ bill_advisor/
COPY api/ api/
COPY app.py .

RUN pip install --no-cache-dir .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
