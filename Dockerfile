FROM python:3.14-slim

#Prevent Python From writting pyc files
ENV PYTHONDONTWRITEBYTECODE=1

#Ensure logs appera Instantly in Terminal
ENV PYTHONUNBUFFERED=1

WORKDIR /app

#Instal system Dependancies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

#Fix UTF-16 Requirements encoding issue automatically
RUN sed -i '1s/^\xEF\xBB\xBF//' requirements.txt || true

# Install dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

#Copy Project files
COPY . .

#Expose Django Port
EXPOSE 8000

#Start server
COPY docker/entrypoint.sh /app/docker/entrypoint.sh

RUN chmod +x /app/docker/entrypoint.sh

ENTRYPOINT ["sh", "/app/docker/entrypoint.sh"]

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
