FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
VOLUME ["/app/output"]
ENV PYTHONPATH=/app/app
CMD ["python", "-m", "bot.handlers"] 