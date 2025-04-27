#!/bin/bash

# Make script exit on first error
set -e

# Check if .env file exists, if not create from example
if [ ! -f .env ]; then
    echo "Creating .env file from env.docker.example..."
    cp env.docker.example .env
    echo "Please edit the .env file with your specific settings."
    exit 1
fi

# Create required directories
mkdir -p deployment/nginx
mkdir -p media
mkdir -p staticfiles

# Check if development or production
if [ "$1" == "dev" ]; then
    echo "Starting development environment..."
    docker-compose -f docker-compose.dev.yml up -d
    
    echo "Creating superuser..."
    docker-compose -f docker-compose.dev.yml exec web python manage.py createsuperuser
    
    echo "Development environment is now running at http://localhost:8000"
else
    echo "Starting production environment..."
    docker-compose up -d
    
    echo "Creating superuser..."
    docker-compose exec web python manage.py createsuperuser
    
    echo "Production environment is now running. Please configure your DNS to point to this server."
fi 