#!/usr/bin/env python
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
env_file = Path('.env')
if env_file.exists():
    load_dotenv()

# Required environment variables
REQUIRED_VARS = [
    'SECRET_KEY',
    'ALLOWED_HOSTS',
]

# Optional but recommended variables
RECOMMENDED_VARS = [
    'DEBUG',
    'DATABASE_URL',
]

# Check required variables
missing_vars = []
for var in REQUIRED_VARS:
    if not os.environ.get(var):
        missing_vars.append(var)

# Check recommended variables
missing_recommended = []
for var in RECOMMENDED_VARS:
    if not os.environ.get(var):
        missing_recommended.append(var)

# Print results
print("=== Environment Variable Check ===")
print()

if missing_vars:
    print("❌ MISSING REQUIRED VARIABLES:")
    for var in missing_vars:
        print(f"   - {var}")
    print()
else:
    print("✅ All required variables are set.")
    print()

if missing_recommended:
    print("⚠️ MISSING RECOMMENDED VARIABLES:")
    for var in missing_recommended:
        print(f"   - {var}")
    print()
else:
    print("✅ All recommended variables are set.")
    print()

# Check database configuration
db_url = os.environ.get('DATABASE_URL', '')
if db_url:
    if db_url.startswith('postgres'):
        print("✅ PostgreSQL database configured.")
    elif db_url.startswith('sqlite'):
        print("⚠️ Using SQLite database. Not recommended for production.")
    else:
        print(f"ℹ️ Database URL: {db_url}")
    print()

# Check debug mode
debug = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 't')
if debug:
    print("⚠️ Debug mode is ON. Should be OFF in production.")
else:
    print("✅ Debug mode is OFF, suitable for production.")
print()

# Security check
if os.environ.get('SECRET_KEY') in ('secret-key', 'your-secret-key-here', 'change-me'):
    print("❌ Using default/insecure SECRET_KEY! This must be changed.")
print()

# Allowed hosts check
allowed_hosts = os.environ.get('ALLOWED_HOSTS', '')
if allowed_hosts:
    hosts = allowed_hosts.split(',')
    print(f"ℹ️ Allowed hosts: {', '.join(hosts)}")
    if '*' in hosts:
        print("⚠️ Allowing all hosts ('*'). This is not recommended for production.")
print()

# Check for Supabase configuration if needed
supabase_url = os.environ.get('SUPABASE_URL', '')
supabase_key = os.environ.get('SUPABASE_KEY', '')
if supabase_url and supabase_key:
    print("✅ Supabase configuration detected.")
else:
    print("ℹ️ Supabase configuration not found.")

print()
print("=== Environment Check Complete ===")

# Exit with error code if required variables are missing
if missing_vars:
    sys.exit(1) 