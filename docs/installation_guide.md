# Amaravathi RMC Management System - Installation Guide

This guide provides step-by-step instructions for installing and configuring the Amaravathi RMC Management System in different environments.

## Prerequisites

### System Requirements
- Python 3.9 or higher
- PostgreSQL 13+ or SQLite (for development)
- 2GB RAM minimum (4GB recommended)
- 10GB free disk space

### Required Software
- Git
- Python and pip
- Virtual environment tool (venv or virtualenv)
- Web server (for production: Nginx or Apache)

## Local Development Installation

### Step 1: Clone the Repository
```bash
git clone https://github.com/teja499-tech/amaravathi-rmcms.git
cd AmaravathiRMCMS
```

### Step 2: Create and Activate Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate on Windows
venv\Scripts\activate

# Activate on macOS/Linux
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
1. Create a `.env` file from the template:
```bash
cp env.example .env
```

2. Open the `.env` file and update the following settings:
```
DEBUG=True
SECRET_KEY=your_secure_secret_key
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
```

For PostgreSQL (optional):
```
DATABASE_URL=postgres://user:password@localhost:5432/amaravathi_db
```

### Step 5: Initialize the Database
```bash
# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### Step 6: Run the Development Server
```bash
python manage.py runserver
```

The system should now be accessible at http://127.0.0.1:8000/

## Production Deployment

### Option 1: Deployment on Render

#### Step 1: Set up a Render Account
1. Sign up at [render.com](https://render.com/)
2. Connect your GitHub repository

#### Step 2: Create a New Web Service
1. From the Render dashboard, click "New" and select "Web Service"
2. Connect to your GitHub repository
3. Use the following settings:
   - **Name**: amaravathi-rmbmp (or your preferred name)
   - **Environment**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn amaravathi_rmbmp.wsgi:application`

#### Step 3: Configure Environment Variables
Add the following environment variables in the Render dashboard:
- `DEBUG`: False
- `SECRET_KEY`: Generate a secure random string
- `ALLOWED_HOSTS`: your-app.onrender.com
- `DATABASE_URL`: Will be automatically set if you create a PostgreSQL database

#### Step 4: Set Up PostgreSQL Database
1. From the Render dashboard, click "New" and select "PostgreSQL"
2. Choose your plan
3. After creation, Render will automatically link the database to your web service

#### Step 5: Deploy
Click "Create Web Service" and wait for the build to complete.

### Option 2: Manual Server Deployment

#### Step 1: Prepare the Server
```bash
# Update packages
sudo apt update
sudo apt upgrade -y

# Install required packages
sudo apt install -y python3-pip python3-venv nginx postgresql postgresql-contrib
```

#### Step 2: Clone the Repository
```bash
git clone https://github.com/teja499-tech/amaravathi-rmcms.git
cd AmaravathiRMCMS
```

#### Step 3: Set Up Python Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn
```

#### Step 4: Configure PostgreSQL
```bash
# Log in as postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE amaravathi_db;
CREATE USER amaravathi_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE amaravathi_db TO amaravathi_user;
\q
```

#### Step 5: Configure Environment Variables
Create a `.env` file with production settings:
```
DEBUG=False
SECRET_KEY=your_secure_secret_key
ALLOWED_HOSTS=your_domain.com,www.your_domain.com
DATABASE_URL=postgres://amaravathi_user:secure_password@localhost:5432/amaravathi_db
```

#### Step 6: Initialize the Database
```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic
```

#### Step 7: Set Up Gunicorn
Create a systemd service file:
```bash
sudo nano /etc/systemd/system/amaravathi.service
```

Add the following content:
```
[Unit]
Description=Amaravathi RMC Management System
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/AmaravathiRMCMS
ExecStart=/path/to/AmaravathiRMCMS/venv/bin/gunicorn --workers 3 --bind unix:/path/to/AmaravathiRMCMS/amaravathi.sock amaravathi_rmbmp.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl enable amaravathi
sudo systemctl start amaravathi
```

#### Step 8: Configure Nginx
Create an Nginx site configuration:
```bash
sudo nano /etc/nginx/sites-available/amaravathi
```

Add the following content:
```
server {
    listen 80;
    server_name your_domain.com www.your_domain.com;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        root /path/to/AmaravathiRMCMS;
    }
    
    location /media/ {
        root /path/to/AmaravathiRMCMS;
    }
    
    location / {
        include proxy_params;
        proxy_pass http://unix:/path/to/AmaravathiRMCMS/amaravathi.sock;
    }
}
```

Enable the site and restart Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/amaravathi /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

#### Step 9: Set Up SSL (Optional but Recommended)
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your_domain.com -d www.your_domain.com
```

## Docker Deployment

### Prerequisites
- Docker
- Docker Compose

### Development Environment Setup

1. Clone the repository:
```bash
git clone https://github.com/teja499-tech/amaravathi-rmcms.git
cd amaravathi-rmcms
```

2. Run the setup script for development:
```bash
./docker-setup.sh dev
```

3. Edit the `.env` file with your specific settings if needed.

4. The application will be available at http://localhost:8000

### Production Environment Setup

1. Clone the repository:
```bash
git clone https://github.com/teja499-tech/amaravathi-rmcms.git
cd amaravathi-rmcms
```

2. Copy the environment example file and configure it:
```bash
cp env.docker.example .env
```

3. Edit the `.env` file with your production settings:
   - Set secure DB_PASSWORD and SECRET_KEY values
   - Configure your DOMAIN
   - Add SUPABASE settings if using Supabase for file storage
   - Configure email settings

4. Run the setup script for production:
```bash
./docker-setup.sh
```

5. Set up SSL with Let's Encrypt:
```bash
# Replace yourdomain.com with your actual domain
docker-compose run --rm certbot certonly --webroot -w /var/www/certbot -d yourdomain.com -d www.yourdomain.com
```

6. Restart the services:
```bash
docker-compose down
docker-compose up -d
```

7. Access your application via your domain.

### Docker Architecture

The Docker deployment consists of three main services:

1. **Web**: The Django application running with Gunicorn
2. **Database**: PostgreSQL database
3. **Nginx**: Web server and reverse proxy

The configuration is defined in the following files:
- `Dockerfile`: Defines the web application container
- `docker-compose.yml`: Main production configuration
- `docker-compose.dev.yml`: Development configuration
- `deployment/nginx/default.conf`: Nginx configuration

### Docker Management Commands

Start the application:
```bash
docker-compose up -d
```

Stop the application:
```bash
docker-compose down
```

View logs:
```bash
docker-compose logs -f web
```

Run migrations:
```bash
docker-compose exec web python manage.py migrate
```

Create a superuser:
```bash
docker-compose exec web python manage.py createsuperuser
```

Restart a specific service:
```bash
docker-compose restart web
```

Rebuild containers after code changes:
```bash
docker-compose up -d --build
```

### Data Persistence

Docker uses volumes to persist data:
- `postgres_data`: PostgreSQL database data
- `static_volume`: Django static files
- `media_volume`: User-uploaded media files
- `certbot_volume`: SSL certificates

These volumes ensure your data survives container restarts and updates.

## Post-Installation Tasks

### Initialize System Settings
1. Log in to the admin panel using the superuser credentials
2. Navigate to "Administration" > "Settings"
3. Configure company information, regional settings, and system preferences

### Set Up User Accounts
1. Create accounts for administrative staff
2. Assign appropriate roles (Admin, Accountant, Viewer)
3. Communicate temporary passwords to users

### Import Initial Data (Optional)
If migrating from another system:
1. Prepare data in CSV format
2. Use the import tools available in the admin panel
3. Verify that all data was imported correctly

## Troubleshooting

### Database Connection Issues
- Verify database credentials in the `.env` file
- Ensure the database server is running
- Check network connectivity between the application and database servers

### Static Files Not Loading
- Run `python manage.py collectstatic` again
- Check file permissions on the static directory
- Verify Nginx configuration for static file paths

### Application Errors
- Check the application logs: `/var/log/amaravathi/app.log`
- Check the Nginx error logs: `/var/log/nginx/error.log`
- Ensure all dependencies are installed correctly

## Maintenance

### Backing Up the Database
```bash
# For PostgreSQL
pg_dump -U amaravathi_user -d amaravathi_db > backup.sql

# Scheduled backups with cron
0 2 * * * pg_dump -U amaravathi_user -d amaravathi_db > /path/to/backups/amaravathi_$(date +\%Y\%m\%d).sql
```

### Updating the Application
```bash
# Pull latest changes
cd /path/to/AmaravathiRMCMS
git pull

# Activate virtual environment
source venv/bin/activate

# Install updated dependencies
pip install -r requirements.txt

# Apply migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Restart the service
sudo systemctl restart amaravathi
```

## Support and Resources

- GitHub Repository: [AmaravathiRMCMS](https://github.com/teja499-tech/amaravathi-rmcms)
- Issue Tracker: [GitHub Issues](https://github.com/teja499-tech/amaravathi-rmcms/issues)
- Documentation: See the `docs` directory for additional guides 