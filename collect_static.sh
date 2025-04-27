#!/bin/bash

# Collect static files for Django deployment
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Check if the command was successful
if [ $? -eq 0 ]; then
    echo "Static files collected successfully in staticfiles directory"
    echo "Total files:"
    find staticfiles -type f | wc -l
else
    echo "Error collecting static files"
    exit 1
fi

echo "Done!" 