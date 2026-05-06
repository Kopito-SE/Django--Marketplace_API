#!/bin/bash
set -e

# Run migrations
python manage.py migrate --noinput

# Collect static files
python manage.py collectstatic --noinput

# Start the application with gunicorn
exec gunicorn marketplace.wsgi:application --bind 0.0.0.0:8000 --workers 3