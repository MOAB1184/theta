import os
from decouple import config

# Supabase Configuration
SUPABASE_URL = "zfciitaohccwmhbezeut"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpmY2lpdGFvaGNjd21oYmV6ZXV0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU3MTg4MjAsImV4cCI6MjA3MTI5NDgyMH0.Ds4wpLEx1LiRQWefRazVRV6iJ9M2RUlrcheexvYqWWY"
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpmY2lpdGFvaGNjd21oYmV6ZXV0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NTcxODgyMCwiZXhwIjoyMDcxMjk0ODIwfQ.65B3RoYaEV0th9IXTrIjlIJctV2UHoOROwKY56NZpPI"

# JWT Configuration
JWT_SECRET = "your-super-secret-jwt-key-here-please-change-this-in-production"
JWT_ALGORITHM = "HS256"

# Server Configuration
HOST = "0.0.0.0"
PORT = 8001
DEBUG = True

# CORS Origins
CORS_ORIGINS = [
    "http://localhost:8000",
    "http://localhost:3000",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:3000"
]
