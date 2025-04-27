# Supabase Database Setup Guide

This guide explains how to set up and configure your Supabase PostgreSQL database for the Amaravathi RMBMP application.

## Prerequisites

1. A Supabase account - [Sign up here](https://supabase.com/) if you don't have one.
2. The Amaravathi RMBMP application codebase.

## Steps to Configure Supabase

### 1. Create a Supabase Project

1. Log in to your Supabase account.
2. Click on "New Project" and follow the wizard to create a new project.
3. Choose a name for your project (e.g., "amaravathi-rmbmp").
4. Set a secure database password.
5. Choose a region closest to your users.
6. Click "Create new project".

### 2. Get Database Connection URL

1. Once your project is created, go to the "Settings" section in the sidebar.
2. Click on "Database" to view your database settings.
3. Under "Connection string", select "URI" format.
4. Copy the displayed connection string. It will look something like:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-ID].supabase.co:5432/postgres
   ```

### 3. Configure Environment Variables

1. Create or update the `.env` file in your project root with the Supabase connection URL:
   ```
   # Django settings
   DEBUG=True
   SECRET_KEY=your-secret-key

   # Database settings
   SUPABASE_DB_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-ID].supabase.co:5432/postgres
   ```

2. Make sure to replace `[YOUR-PASSWORD]` and `[YOUR-PROJECT-ID]` with the actual values from your Supabase project.

### 4. Migrate Database Schema

Run the following commands to apply the database migrations:

```bash
python manage.py migrate
```

### 5. Creating a Superuser

Create an admin user with:

```bash
python manage.py createsuperuser
```

## Troubleshooting

### Connection Issues

If you're having trouble connecting to the Supabase database:

1. Ensure your IP address is allowed in Supabase. Go to Settings > Database > Network and add your IP to the allow list.
2. Verify that your database password is correct in the connection string.
3. Run the validation command to check the connection:
   ```bash
   python manage.py validate_db_connection
   ```

### SSL Requirements

Supabase requires SSL for connections. If you encounter SSL-related errors, add the following parameters to your connection URL:

```
?sslmode=require
```

So your full URL would be:
```
postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-ID].supabase.co:5432/postgres?sslmode=require
```

## Production Setup

For production environments, make sure to:

1. Set `DEBUG=False` in your .env file
2. Use a proper secret key
3. Configure your allowed hosts
4. Consider using environment variables instead of a .env file for better security

# Setting Up Supabase for File Storage

This project uses Supabase for storing purchase invoice files. Follow these steps to set up Supabase for your development environment.

## 1. Create a Supabase Account

- Go to [https://supabase.com/](https://supabase.com/) and sign up for an account
- Create a new project in Supabase

## 2. Set Up Storage Bucket

- In your Supabase project dashboard, go to Storage
- Create a new bucket named `ameravathi-invoices` (or choose a different name)
- Set the bucket privacy to public (for ease of development)

## 3. Get Your Supabase Credentials

- Go to Project Settings > API
- Copy your `URL` (it looks like `https://xxx.supabase.co`)
- Copy your `anon/public` key (not the service_role key)

## 4. Set Up Environment Variables

Create a `.env` file in the root directory with the following variables:

```
# Supabase Storage Settings
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-supabase-anon-key-here
SUPABASE_BUCKET=ameravathi-invoices
```

Make sure to replace the placeholder values with your actual Supabase credentials.

## 5. Install Required Python Packages

The project already includes the necessary packages in requirements.txt, but you can install them manually if needed:

```bash
pip install supabase python-decouple
```

## 6. Test the Connection

After configuring the environment variables, run the Django development server:

```bash
python manage.py runserver
```

Try to upload a purchase invoice and verify that the file is successfully stored in your Supabase bucket. 