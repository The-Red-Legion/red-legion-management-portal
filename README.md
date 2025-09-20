# 🌐 Red Legion Management Portal

A web interface for the Red Legion Discord bot payroll system with comprehensive mining event management and donation features.

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+
- Access to PostgreSQL database (optional - has mock mode)

### Backend Setup
```bash
cd backend/
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
# → Runs on http://localhost:8000
```

### Frontend Setup
```bash
cd frontend/
npm install
npm run dev
# → Runs on http://localhost:5173
```

## 🎯 Features

- **No Authentication Required** - Direct access for streamlined usage
- **Event Management** - View, create, and close mining/salvage events
- **Payroll Calculator** - Full donation system with redistribution logic
- **Real-time Pricing** - Live UEX ore price integration
- **Admin Functions** - Test event creation, cache refresh, event deletion
- **Mock Mode** - Works offline without database for development

## 🏗️ Architecture

- **Backend**: FastAPI (Python) - No-auth version with full admin capabilities
- **Frontend**: Vue.js + Tailwind CSS - Clean, responsive UI
- **Database**: PostgreSQL with fallback to mock mode
- **Integration**: Bot API integration for UEX price data

## 📁 Structure

```
red-legion-management-portal/
├── backend/          # FastAPI server (no-auth)
│   ├── main.py      # Production server
│   └── archive/     # OAuth version for future use
├── frontend/         # Vue.js app
└── README.md        # This file
```

## 🔧 Development

Both backend and frontend run locally with hot reload for rapid development.

- **Backend**: http://localhost:8000 (API + admin endpoints)
- **Frontend**: http://localhost:5173 (Web interface)
- **Database**: PostgreSQL or mock mode

## 💰 Payroll System

### Event Lifecycle
1. **Event Created** → Gets unique `event_id`
2. **Event Finished** → Status = 'closed', creates payroll with status = 'open'
3. **Calculate Payroll** → Processes donations and calculates redistribution
4. **Close Payroll** → Sets payroll status = 'closed' and saves data

### Donation System
- Users can donate their share to other participants
- Donated amounts are redistributed equally among non-donating participants
- Full transaction logging and proper database persistence

## 🛠️ Admin Features

- **Create Test Events**: `/admin/create-test-event/{event_type}`
- **Delete Events**: `/admin/events/{event_id}`
- **Refresh UEX Cache**: `/admin/refresh-uex-cache`
- **Create Events**: `/events/create`

All admin endpoints support both `/admin/` and `/mgmt/api/admin/` prefixes for production compatibility.

## 🚀 Deployment

See `DEPLOYMENT.md` for complete deployment instructions using GitHub Actions and Ansible.