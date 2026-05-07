FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

# Non-root user for security
RUN useradd -m -u 1000 sreagent
USER sreagent

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
