# 🚀 SAMVAD Backend

The powerful backend API for SAMVAD - A comprehensive campus community platform built with FastAPI.

## 📋 What is SAMVAD Backend?

SAMVAD Backend is a modern REST API that powers the entire SAMVAD campus community platform. It handles:

- 👥 **User Management** - Registration, login, Google OAuth
- 🏛️ **Club Management** - Create, join, and manage campus clubs
- 📅 **Event Management** - Organize and register for events
- 🤖 **AI Features** - Face recognition for attendance
- 📸 **Photo Gallery** - Upload and manage event photos
- 💬 **Forums** - Discussion boards for community interaction
- 🔐 **Role-Based Access** - Student, Club Admin, Super Admin roles
- 📱 **WhatsApp Integration** - OTP verification system

## 🛠️ Technology Stack

- **Framework**: FastAPI (Python)
- **Database**: SQLite (development) / PostgreSQL (production)
- **Authentication**: JWT tokens + Google OAuth
- **File Storage**: Cloudinary
- **AI/ML**: Face Recognition library
- **Communication**: Twilio (WhatsApp)
- **Deployment**: Render.com

## 🚀 Quick Start

### Prerequisites
- Python 3.11 or higher
- Git

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd samvad-backend
```

### 2. Create Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate it (Windows)
venv\Scripts\activate

# Activate it (Mac/Linux)
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables
Create a `.env` file in the root directory:
```bash
# Copy the example file
copy .env.example .env

# Edit .env with your actual values
```

Required environment variables:
```bash
# Database
DATABASE_URL=sqlite:///./samvad.db

# JWT Security
JWT_SECRET_KEY=your-super-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Cloudinary (for file uploads)
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

# Twilio (optional - for WhatsApp OTP)
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+1234567890
```

### 5. Run the Application
```bash
# Start the development server
uvicorn app.main:app --reload

# Or use the batch file (Windows)
start_backend.bat
```

The API will be available at: `http://localhost:8000`

### 6. View API Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 📁 Project Structure

```
samvad-backend/
├── app/
│   ├── api/
│   │   ├── routes/          # API endpoint routes
│   │   │   ├── users.py     # User authentication & management
│   │   │   ├── clubs.py     # Club management
│   │   │   ├── events.py    # Event management
│   │   │   ├── photos.py    # Photo gallery
│   │   │   ├── attendance.py # AI attendance system
│   │   │   ├── forums.py    # Discussion forums
│   │   │   ├── admin.py     # Admin operations
│   │   │   └── role_requests.py # Role upgrade requests
│   │   └── deps.py          # Dependencies
│   ├── core/
│   │   ├── config.py        # Configuration settings
│   │   ├── security.py      # JWT & password handling
│   │   ├── super_admin_config.py # Super admin whitelist
│   │   └── cloudinary_utils.py   # File upload utilities
│   ├── db/
│   │   ├── database.py      # Database connection
│   │   └── models.py        # Database models
│   ├── schemas.py           # Pydantic schemas
│   └── main.py             # FastAPI application
├── requirements.txt         # Python dependencies
├── .env.example            # Environment variables template
└── README.md              # This file
```

## 🔐 User Roles & Permissions

### 1. Student (Default)
- Browse clubs and events
- Join clubs and register for events
- Enroll face for AI attendance
- Participate in forums
- View photo gallery

### 2. Club Admin
- All student permissions
- Create and manage clubs
- Create events for their clubs
- Upload photos
- Start AI attendance sessions
- Manage club members

### 3. Super Admin
- All permissions
- Manage all users and roles
- System-wide club oversight
- Platform analytics
- User role management

## 🔧 API Endpoints

### Authentication
- `POST /users/signup` - User registration
- `POST /users/login` - User login
- `POST /users/google-login` - Google OAuth login
- `GET /users/me` - Get current user info

### Clubs
- `GET /clubs/` - List all clubs
- `POST /clubs/` - Create new club (Club Admin+)
- `GET /clubs/{id}` - Get club details
- `POST /clubs/{id}/join` - Join a club

### Events
- `GET /events/` - List all events
- `POST /events/` - Create new event (Club Admin+)
- `GET /events/{id}` - Get event details
- `POST /events/{id}/register` - Register for event

### Photos
- `GET /photos/gallery` - Get photo gallery
- `POST /photos/gallery` - Upload photo (Club Admin+)
- `POST /events/{id}/photos` - Upload event photo

### Admin (Super Admin only)
- `GET /admin/users` - List all users
- `PUT /admin/users/{id}/role` - Update user role
- `DELETE /admin/users/{id}` - Delete user

## 🤖 AI Features

### Face Recognition Attendance
1. **Face Enrollment**: Users upload their photo
2. **Live Attendance**: Club admins start attendance sessions
3. **Recognition**: System recognizes faces in real-time
4. **Marking**: Automatic attendance marking

## 🔒 Security Features

- **JWT Authentication** - Secure token-based auth
- **Password Hashing** - Bcrypt encryption
- **Role-Based Access** - Granular permissions
- **Super Admin Whitelist** - Email-based admin control
- **Input Validation** - Pydantic schemas
- **CORS Protection** - Cross-origin security

## 🚀 Deployment

### Local Development
```bash
uvicorn app.main:app --reload
```

### Production (Render.com)
1. Push code to GitHub
2. Create Render web service
3. Set environment variables
4. Deploy automatically

See `DEPLOYMENT_GUIDE.md` for detailed instructions.

## 🧪 Testing

```bash
# Run tests (if available)
pytest

# Check code style
flake8 app/

# Type checking
mypy app/
```

## 📊 Database

### Development
- Uses SQLite database (`samvad.db`)
- Automatically created on first run
- Perfect for local development

### Production
- Uses PostgreSQL on Render
- Automatic migrations
- Scalable and reliable

## 🔧 Configuration

### Environment Variables
All configuration is done through environment variables:

- `DATABASE_URL` - Database connection string
- `JWT_SECRET_KEY` - JWT signing key (keep secret!)
- `CLOUDINARY_*` - File upload credentials
- `TWILIO_*` - WhatsApp OTP credentials

### Super Admin Setup
Edit `app/core/super_admin_config.py`:
```python
SUPER_ADMIN_EMAILS = {
    "admin@yourschool.edu",
    "owner@yourschool.edu",
}
```

## 🐛 Troubleshooting

### Common Issues

**Database Connection Error**
```bash
# Check DATABASE_URL format
DATABASE_URL=sqlite:///./samvad.db  # Local
DATABASE_URL=postgresql://user:pass@host:port/db  # Production
```

**Import Errors**
```bash
# Reinstall dependencies
pip install -r requirements.txt
```

**Permission Errors**
```bash
# Check user roles in database
# Verify super admin emails in config
```

### Debug Mode
```bash
# Run with debug logging
uvicorn app.main:app --reload --log-level debug
```

## 📞 Support

- **Documentation**: Check `/docs` endpoint
- **Issues**: Create GitHub issue
- **Email**: Contact your development team

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit pull request

## 📄 License

This project is part of the SAMVAD campus community platform.

---

**Made with ❤️ for campus communities**
