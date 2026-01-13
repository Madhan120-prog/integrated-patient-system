# XYZ Hospital - Unified Patient Data Retrieval System

## Product Overview
A full-stack healthcare application for hospital staff to search, view, and analyze patient medical records across multiple departments. Features an AI-powered clinical assistant (DocAssist) for voice-enabled natural language queries about patient records.

## Tech Stack
- **Frontend**: React, React Router, Axios, Tailwind CSS, Shadcn UI, Recharts
- **Backend**: FastAPI, Pydantic, Motor (async MongoDB)
- **Database**: MongoDB
- **AI Integration**: OpenAI GPT-5.2 via Emergent LLM Key (emergentintegrations library)
- **Voice**: Web Speech API (browser-native speech-to-text and text-to-speech)

## User Personas
- **Doctors**: Primary users who need quick access to patient records and AI-assisted analysis
- **Nurses**: Support staff needing to verify patient information
- **Administrators**: System oversight and management

## Core Features

### ✅ Implemented Features

#### 1. Authentication System
- Secure login for hospital staff
- Role-based access (Doctor, Nurse, Admin)
- Demo credentials available

#### 2. Patient Search & Records
- Search by Patient ID (e.g., P1001) or Name
- Partial name matching supported
- Department-wise record display (MRI, X-Ray, ECG, Blood Profile, CT Scan, Treatment)
- Chronological sorting of records

#### 3. Patient Analytics Dashboard
- Visit breakdown charts (bar and pie charts using Recharts)
- Treatment progress tracking
- Health trend indicators
- Department visit statistics

#### 4. DocAssist - Voice AI Clinical Assistant (NEW - Dec 2025)
- **Voice Input**: Microphone button using Web Speech API (speech-to-text)
- **Voice Output**: AI responses spoken aloud (text-to-speech) with mute toggle
- **AI Backend**: OpenAI GPT-5.2 via `/api/deep-query` endpoint
- **Features**:
  - Patient search and confirmation flow
  - Natural language questions about medical records
  - Evidence cards with supporting records
  - Department matching tags
  - Voice On/Off toggle

#### 5. Department Views
- Individual department record tables
- Sortable columns
- All-patient view per department

#### 6. Custom Branding
- XYZ Hospital name and logo
- Custom SVG icons for medical departments
- Professional healthcare UI theme

### 📋 Upcoming Tasks (P1)
1. **PDF Export & Reporting**: Generate downloadable PDF summaries of patient records
2. **Advanced Search & Filters**: Date range filters, result status filters, doctor filters
3. **Management Dashboard**: Hospital-wide analytics for administrators

### 🗂️ Future/Backlog (P2)
- Patient History Timeline Visualization
- Smart Notifications for critical results
- Doctor Collaboration Tools (notes, referrals)
- Mobile Optimization & QR Code Scanning
- Audit Logs for HIPAA compliance
- Patient Portal for self-service record access

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/` | GET | API health check |
| `/api/login` | POST | User authentication |
| `/api/init-data` | POST | Initialize sample data |
| `/api/patients` | GET | List all patients |
| `/api/search?term=` | GET | Search patient by ID or name |
| `/api/analytics/{patient_id}` | GET | Get patient analytics |
| `/api/department/{name}` | GET | Get department records |
| `/api/deep-query` | POST | AI clinical assistant query |

## Database Schema

**Database**: `hospital_db`

**Collections**:
- `profiles` - Patient demographics
- `users` - Staff credentials and roles
- `mri_records` - MRI scan results
- `xray_records` - X-Ray results
- `ecg_records` - ECG test results
- `blood_profile_records` - Blood test results
- `ct_scan_records` - CT scan results
- `treatment_records` - Treatment history with medicines

## Test Credentials
- **Doctor**: `doctor` / `doctor123`
- **Nurse**: `nurse` / `nurse123`
- **Admin**: `admin` / `admin123`

## Key Files
- `/app/backend/server.py` - All API endpoints
- `/app/frontend/src/components/DeepSearchModal.jsx` - DocAssist modal
- `/app/frontend/src/pages/SearchPage.jsx` - Main search interface
- `/app/backend/.env` - Environment configuration

## Testing
- **Backend Tests**: 19/19 tests passing (`/app/tests/test_docassist_api.py`)
- **Test Reports**: `/app/test_reports/iteration_1.json`

---
*Last Updated: January 2026*
