# Scout Accelerator Backend API

A FastAPI backend for the Scout Accelerator scouting management platform.

## Features

- **User Authentication**: JWT-based authentication with role-based access control
- **Scouting Management**: Complete API for troop management, rank advancement, and sign-off requests
- **Real-time Data**: Integration with Supabase for real-time database operations
- **Secure**: Password hashing, JWT tokens, and secure API endpoints
- **CORS Enabled**: Ready for frontend integration

## Tech Stack

- **FastAPI**: Modern, fast web framework for building APIs
- **Supabase**: Backend-as-a-Service for database and real-time features
- **JWT**: JSON Web Tokens for authentication
- **bcrypt**: Password hashing
- **Python 3.8+**: Core programming language

## Installation

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   - Update `config.py` with your Supabase credentials
   - Change the JWT secret key for production

3. **Run the Server**
   ```bash
   python app.py
   ```

   Or with uvicorn:
   ```bash
   uvicorn app:app --host 0.0.0.0 --port 8001 --reload
   ```

## API Endpoints

### Authentication
- `POST /auth/signup` - User registration
- `POST /auth/login` - User login

### Dashboard
- `GET /dashboard/scout` - Scout dashboard data
- `GET /dashboard/scoutmaster` - Scoutmaster dashboard data

### Requirements & Advancement
- `GET /requirements/{rank}` - Get requirements for a specific rank
- `POST /signoff-request` - Create sign-off request
- `POST /conference-request` - Create conference request

## Database Schema

The backend works with the following Supabase tables:
- `users` - User accounts and profiles
- `troops` - Troop information and settings
- `patrols` - Patrol management
- `requirements` - Rank requirements
- `user_requirements` - User progress tracking
- `signoff_requests` - Sign-off request management
- `conferences` - Scoutmaster conferences
- `events` - Troop events

## Authentication

The API uses JWT (JSON Web Tokens) for authentication:
1. Users login/signup to receive a JWT token
2. Include the token in the Authorization header: `Bearer <token>`
3. The token is valid for 30 minutes

## Error Handling

The API returns standard HTTP status codes:
- `200` - Success
- `400` - Bad Request
- `401` - Unauthorized
- `404` - Not Found
- `500` - Internal Server Error

Error responses include a `detail` field with error description.

## Development

### Running in Development Mode
```bash
python app.py
```

### API Documentation
When running the server, visit:
- Swagger UI: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`

### Testing
```bash
# Install test dependencies
pip install pytest httpx

# Run tests
pytest
```

## Production Deployment

1. Set `DEBUG = False` in config
2. Use a production WSGI server (gunicorn)
3. Set up proper environment variables
4. Configure CORS origins for your frontend domain
5. Use a secure JWT secret key
6. Set up HTTPS

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is part of Scout Accelerator - a free platform for scouting organizations.
