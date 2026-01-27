# 🏥 XYZ Hospital Patient Records - Local Setup Guide

This guide will help you run the complete Patient Records Portal with DocAssist AI on your local MacBook **without any Emergent dependencies**.

---

## 📋 Prerequisites

| Requirement | Version | Check Command |
|-------------|---------|---------------|
| **Node.js** | 18+ | `node --version` |
| **Python** | 3.10+ | `python3 --version` |
| **MongoDB** | 6.0+ | `mongod --version` |
| **Yarn** | 1.22+ | `yarn --version` |

---

## 🔑 API Keys Required

You'll need **one** of these for AI features:

| Provider | Model Used | Get Key From |
|----------|------------|--------------|
| **OpenAI** (Recommended) | GPT-4o | https://platform.openai.com/api-keys |

> **Note:** OpenAI GPT-4o handles both text analysis AND image/vision analysis, so you only need one API key.

---

## 🚀 Quick Start (5 Steps)

### Step 1: Install MongoDB

```bash
# macOS with Homebrew
brew tap mongodb/brew
brew install mongodb-community@7.0
brew services start mongodb-community@7.0

# Verify MongoDB is running
mongosh --eval "db.adminCommand('ping')"
# Should output: { ok: 1 }
```

### Step 2: Clone/Download the Project

```bash
# If you have the project as a zip, extract it
# Or clone from your repository
cd /path/to/project
```

### Step 3: Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements_local.txt

# Create .env file
cat > .env << 'EOF'
MONGO_URL=mongodb://localhost:27017
DB_NAME=hospital_db
OPENAI_API_KEY=sk-your-openai-api-key-here
EOF

# Start the backend
python server_local.py
# Or with auto-reload:
uvicorn server_local:app --reload --port 8001
```

### Step 4: Frontend Setup

```bash
# Open a new terminal
cd frontend

# Install dependencies
yarn install

# Create .env file
cat > .env << 'EOF'
REACT_APP_BACKEND_URL=http://localhost:8001
EOF

# Start the frontend
yarn start
```

### Step 5: Initialize Sample Data

```bash
# In a new terminal, initialize the database
curl -X POST http://localhost:8001/api/init-data
```

---

## 🌐 Access the Application

| Component | URL |
|-----------|-----|
| **Frontend** | http://localhost:3000 |
| **Backend API** | http://localhost:8001/api |
| **API Docs** | http://localhost:8001/docs |

### Test Credentials
- **Doctor:** `doctor` / `doctor123`
- **Nurse:** `nurse` / `nurse123`
- **Admin:** `admin` / `admin123`

---

## 📁 Project Structure

```
project/
├── backend/
│   ├── server_local.py      # Main FastAPI app (OpenAI direct)
│   ├── requirements_local.txt
│   ├── .env                  # Your API keys
│   └── uploads/              # Temp files for analysis
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── DeepSearchModal.jsx  # DocAssist UI
│   │   │   └── ui/                   # Shadcn components
│   │   └── pages/
│   │       ├── SearchPage.jsx
│   │       ├── ResultsPageDepartments.jsx
│   │       └── ...
│   ├── package.json
│   └── .env
└── LOCAL_SETUP.md           # This file
```

---

## 🔧 Backend Requirements (requirements_local.txt)

```txt
fastapi==0.109.0
uvicorn==0.27.0
motor==3.3.2
pydantic==2.5.3
python-dotenv==1.0.0
faker==22.0.0
python-multipart==0.0.6
openai==1.12.0
pdfplumber==0.10.3
Pillow==10.2.0
httpx==0.26.0
```

---

## 🤖 AI Features Explained

### 1. DocAssist Chat (`/api/deep-query`)
- Uses **OpenAI GPT-4o** for natural language understanding
- Analyzes all patient records in context
- Maintains conversation memory within session
- Falls back to rule-based summaries if API unavailable

### 2. Document Analysis (`/api/analyze-document`)
- **Images (X-Ray, MRI, CT):** OpenAI Vision API (GPT-4o)
- **PDFs:** Text extraction with pdfplumber + GPT-4o analysis
- Returns structured findings with abnormality flags

### 3. Fallback Strategy
When OpenAI is unavailable:
- Rule-based patient summaries
- Basic abnormality detection from stored results
- Clear "AI unavailable" messaging (no UI breakage)

---

## 🩺 Clinical System Prompt

The AI uses a carefully designed prompt that:

```
✅ Grounds every answer in actual patient records
✅ Flags abnormal values explicitly: "⚠️ ABNORMAL: [value]"
✅ Uses cautious language: "Records indicate..." not "You have..."
✅ Never diagnoses or prescribes
✅ Always recommends physician review for abnormals
```

---

## 🛠️ Troubleshooting

### MongoDB Connection Issues
```bash
# Check if MongoDB is running
brew services list | grep mongodb

# Restart MongoDB
brew services restart mongodb-community@7.0

# Check logs
tail -f /usr/local/var/log/mongodb/mongo.log
```

### OpenAI API Errors
```bash
# Verify API key is set
echo $OPENAI_API_KEY

# Test API directly
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Port Already in Use
```bash
# Find process using port 8001
lsof -i :8001

# Kill process
kill -9 <PID>

# Or use different port
uvicorn server_local:app --port 8002
```

### Frontend Can't Connect to Backend
1. Check backend is running: `curl http://localhost:8001/api/`
2. Verify REACT_APP_BACKEND_URL in frontend/.env
3. Check for CORS errors in browser console

---

## 📊 API Endpoints Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/` | GET | Health check |
| `/api/login` | POST | User authentication |
| `/api/init-data` | POST | Initialize sample data |
| `/api/search?term=` | GET | Search patients |
| `/api/analytics/{id}` | GET | Patient analytics |
| `/api/department/{name}` | GET | Department records |
| `/api/deep-query` | POST | AI chat assistant |
| `/api/analyze-document` | POST | File analysis |
| `/api/health` | GET | System health status |

---

## 🔒 Security Notes

1. **Never commit .env files** to version control
2. **Rotate API keys** periodically
3. **Use environment variables** in production
4. For production deployment, add proper authentication

---

## 💰 Cost Estimation (OpenAI)

| Feature | Model | Est. Cost per Query |
|---------|-------|---------------------|
| DocAssist Chat | GPT-4o | ~$0.01-0.03 |
| Image Analysis | GPT-4o Vision | ~$0.02-0.05 |
| PDF Analysis | GPT-4o | ~$0.01-0.02 |

> Tip: Set usage limits in your OpenAI dashboard to control costs.

---

## 🚀 Production Deployment Options

1. **Docker** - Containerize both frontend and backend
2. **Vercel** (Frontend) + **Railway** (Backend + MongoDB)
3. **AWS** - EC2 + DocumentDB
4. **Google Cloud** - Cloud Run + MongoDB Atlas

---

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review backend logs: `tail -f backend/logs/app.log`
3. Check browser console for frontend errors

---

## ✅ Feature Checklist

| Feature | Status |
|---------|--------|
| Patient Search | ✅ Works locally |
| Patient Analytics | ✅ Works locally |
| Department Views | ✅ Works locally |
| DocAssist Chat | ✅ With OpenAI key |
| Voice Input | ✅ Browser Speech API |
| Voice Output | ✅ Browser Speech API |
| File Upload | ✅ Works locally |
| Image Analysis | ✅ With OpenAI key |
| PDF Analysis | ✅ With OpenAI key |
| Fullscreen Mode | ✅ Works locally |
| Context Memory | ✅ Works locally |

---

**Happy coding! 🎉**
