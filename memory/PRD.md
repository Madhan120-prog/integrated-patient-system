# XYZ Hospital - Unified Patient Data Retrieval System

## Product Overview
A full-stack healthcare application for hospital staff to search, view, and analyze patient medical records across multiple departments. Features an AI-powered clinical assistant (DocAssist) for voice-enabled natural language queries about patient records and document analysis.

## Tech Stack
- **Frontend**: React, React Router, Axios, Tailwind CSS, Shadcn UI, Recharts
- **Backend**: FastAPI, Pydantic, Motor (async MongoDB)
- **Database**: MongoDB
- **AI Integration**: 
  - OpenAI GPT-5.2 via Emergent LLM Key for text queries
  - Gemini 2.5 Flash via Emergent LLM Key for file/document analysis
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

#### 4. DocAssist - Voice AI Clinical Assistant
- **Voice Input**: Microphone button using Web Speech API (speech-to-text)
- **Voice Output**: AI responses spoken aloud (text-to-speech) with mute toggle
- **AI Backend**: OpenAI GPT-5.2 via `/api/deep-query` endpoint
- **Features**:
  - Patient search and confirmation flow
  - Natural language questions about medical records
  - Evidence cards with supporting records
  - Department matching tags
  - Voice On/Off toggle
  - Microphone permission help text

#### 5. View Report Feature (NEW - Jan 2026)
- **View Report Button**: On each evidence card with report images
- **Report Modal**: Opens medical images in a modal with:
  - Full-size image display
  - "Open in New Tab" option
  - Close button
- Shows doctor name on evidence cards

#### 6. File Upload & AI Analysis (NEW - Jan 2026)
- **Upload Files**: PNG, JPEG, WebP images and PDF documents
- **Gemini AI Analysis**: Uses Gemini 2.5 Flash for document analysis
- **Features**:
  - File type validation
  - 10MB file size limit
  - AI-generated medical document summaries
  - Suggestions for follow-up actions
- **Endpoint**: `POST /api/analyze-document`

#### 7. Department Views
- Individual department record tables
- Sortable columns
- All-patient view per department

#### 8. Custom Branding
- XYZ Hospital name and logo
- Custom SVG icons for medical departments
- Professional healthcare UI theme

### 📋 Upcoming Tasks (P1)
1. **Real Dataset Integration**: User will provide medical datasets to replace sample data
2. **PDF Export & Reporting**: Generate downloadable PDF summaries of patient records
3. **Advanced Search & Filters**: Date range filters, result status filters, doctor filters

### 🗂️ Future/Backlog (P2)
- Management Dashboard with hospital-wide analytics
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
| `/api/deep-query` | POST | AI clinical assistant query (GPT-5.2) |
| `/api/analyze-document` | POST | File upload & analysis (Gemini) |

## Database Schema

**Database**: `hospital_db`

**Collections**:
- `profiles` - Patient demographics
- `users` - Staff credentials and roles
- `mri_records` - MRI scan results (with report_image)
- `xray_records` - X-Ray results (with report_image)
- `ecg_records` - ECG test results (with report_image)
- `blood_profile_records` - Blood test results (with report_image)
- `ct_scan_records` - CT scan results (with report_image)
- `treatment_records` - Treatment history with medicines

## Test Credentials
- **Doctor**: `doctor` / `doctor123`
- **Nurse**: `nurse` / `nurse123`
- **Admin**: `admin` / `admin123`

## Key Files
- `/app/backend/server.py` - All API endpoints
- `/app/frontend/src/components/DeepSearchModal.jsx` - DocAssist modal with View Report and File Upload
- `/app/frontend/src/pages/SearchPage.jsx` - Main search interface
- `/app/backend/.env` - Environment configuration

## Testing
- **Backend Tests**: 27/27 tests passing (`/app/tests/test_docassist_api.py`)
- **Test Reports**: `/app/test_reports/iteration_2.json`

## Data Notes
- Currently using **Faker library** to generate static sample data
- Data persists in MongoDB (not regenerated on restart)
- User will provide real medical datasets later for replacement

---
*Last Updated: January 2026*
