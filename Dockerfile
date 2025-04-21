FROM python:3.8-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=wsgi.py
ENV FLASK_ENV=production
ENV SECRET_KEY=scanmark-production-key-2025

EXPOSE 10000

CMD ["gunicorn", "--bind", "0.0.0.0:10000", "wsgi:app"]
