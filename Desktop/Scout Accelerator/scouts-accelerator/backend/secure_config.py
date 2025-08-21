"""
Secure Configuration for Scout Accelerator Backend
This file contains sensitive configuration data.
In production, move these to environment variables.
"""

import os
from decouple import config

# Supabase Configuration
SUPABASE_CONFIG = {
    "url": config('SUPABASE_URL', default="https://zfciitaohccwmhbezeut.supabase.co"),
    "anon_key": config('SUPABASE_ANON_KEY', default="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpmY2lpdGFvaGNjd21oYmV6ZXV0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU3MTg4MjAsImV4cCI6MjA3MTI5NDgyMH0.Ds4wpLEx1LiRQWefRazVRV6iJ9M2RUlrcheexvYqWWY"),
    "service_role_key": config('SUPABASE_SERVICE_ROLE_KEY', default="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpmY2lpdGFvaGNjd21oYmV6ZXV0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NTcxODgyMCwiZXhwIjoyMDcxMjk0ODIwfQ.65B3RoYaEV0th9IXTrIjlIJctV2UHoOROwKY56NZpPI")
}

# JWT Configuration
JWT_CONFIG = {
    "secret": config('JWT_SECRET', default="CHANGE_THIS_JWT_SECRET_IN_PRODUCTION_ENVIRONMENT_VARIABLES"),
    "algorithm": "HS256",
    "access_token_expire_minutes": int(config('JWT_ACCESS_TOKEN_EXPIRE_MINUTES', default=30))
}

# Server Configuration
SERVER_CONFIG = {
    "host": config('SERVER_HOST', default="0.0.0.0"),
    "port": int(config('SERVER_PORT', default=8001)),
    "debug": config('DEBUG', default=False, cast=bool)
}

# CORS Origins - More restrictive in production
CORS_ORIGINS = config('CORS_ORIGINS', default="http://localhost:8000,http://localhost:3000,http://127.0.0.1:8000,http://127.0.0.1:3000").split(',')

# Demo Accounts - Only in development
DEMO_ACCOUNTS = {}
if config('DEVELOPMENT_MODE', default=False, cast=bool):
    DEMO_ACCOUNTS = {
        "scoutmaster@demo.com": config('DEMO_SCOUTMASTER_PASSWORD', default="StrongDemoPass123!"),
        "scout@demo.com": config('DEMO_SCOUT_PASSWORD', default="StrongDemoPass123!"),
        "admin@demo.com": config('DEMO_ADMIN_PASSWORD', default="StrongAdminPass123!")
    }

# Security Warning
SECURITY_WARNING = """
⚠️  SECURITY NOTICE  ⚠️

This configuration file contains sensitive information including:
- Supabase API keys
- JWT secret keys
- Demo account credentials

For production deployment:
1. Move all sensitive data to environment variables
2. Use a secure secret management system
3. Change all default passwords and keys
4. Enable HTTPS
5. Set DEBUG = False
6. Configure proper CORS origins
7. Use strong, unique passwords for demo accounts

Never commit this file to version control with real credentials!
"""
