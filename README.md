# ApexPath - AI-Powered Cycling Training

Your AI-powered cycling training companion with Strava integration, adaptive training plans, and workout export to Zwift, MyWhoosh, and Rouvy.

## Features

- **Strava Integration** - Automatic activity sync with OAuth2
- **Fitness Tracking** - CTL, ATL, TSB metrics calculated from power data
- **Training Plans** - Polarized, Sweet Spot, and Traditional periodization
- **Workout Export** - Export to ZWO (Zwift/MyWhoosh) and MRC (Rouvy) formats
- **PWA** - Install as app on mobile or desktop

## Tech Stack

### Frontend
- React 19 + TypeScript
- Vite + PWA
- TailwindCSS
- Recharts for visualizations
- React Big Calendar
- Zustand for state management

### Backend
- Python + FastAPI
- SQLAlchemy + SQLite
- Strava API integration

## Getting Started

### Prerequisites
- Node.js 18+
- Python 3.11+
- Strava API credentials

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # Edit with your Strava credentials
uvicorn app.main:app --reload
```

### Frontend Setup
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

## Environment Variables

### Backend (.env)
```
STRAVA_CLIENT_ID=your_client_id
STRAVA_CLIENT_SECRET=your_client_secret
SECRET_KEY=your_secret_key
```

### Frontend (.env)
```
VITE_API_URL=http://localhost:8000/api
```

## License

MIT
