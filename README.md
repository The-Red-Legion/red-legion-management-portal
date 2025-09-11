# 🌐 Red Legion Web Payroll

A simplified web interface for the Red Legion Discord bot payroll system.

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+
- Access to existing PostgreSQL database

### Backend Setup
```bash
cd backend/
pip install -r requirements.txt
python main.py
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

- **Discord OAuth Login** - Same authentication as bot
- **Event Selection** - Choose mining events from database
- **Payroll Wizard** - Same 4-step process as Discord bot
- **Amount Overrides** - Set custom participant amounts
- **Real-time UEX Pricing** - Live ore price integration

## 🏗️ Architecture

- **Backend**: FastAPI (Python) - Reuses bot's database logic
- **Frontend**: Vue.js + Tailwind CSS - Clean, responsive UI
- **Database**: Shared PostgreSQL with Discord bot
- **Auth**: Discord OAuth for seamless integration

## 📁 Structure

```
red-legion-website/
├── backend/          # FastAPI server
├── frontend/         # Vue.js app
├── static/          # Images, assets
└── README.md        # This file
```

## 🔧 Development

Both backend and frontend run locally with hot reload for rapid development.

**Backend**: http://localhost:8000
**Frontend**: http://localhost:5173
**Database**: Your existing PostgreSQL instance