# Unnati

Unnati is an AI-powered sports talent assessment platform that evaluates athlete fitness tests from uploaded or recorded videos. The system combines a React web application with a FastAPI backend and MediaPipe-based pose analysis to generate scores, grades, confidence values, form metrics, and validation flags.

## Features

- Mobile-first React web interface
- Athlete authentication and protected routes
- Video upload and webcam-based test recording
- Rear/front camera switching support
- AI-assisted analysis for selected fitness tests
- Result cards with score, grade, confidence, form score, cheat score, and detailed metrics
- History and leaderboard views
- FastAPI backend with Swagger documentation
- SQLite-backed local development database
- MediaPipe/OpenCV pose extraction pipeline

## Supported Tests

- T3: Sit and Reach
- T4: Vertical Jump
- T5: Standing Broad Jump
- T8: Shuttle Run
- T9: Sit-Ups

## Project Structure

```text
.
├── sports-assessment-frontend/   # React + Vite frontend
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── sports-assessment-backend/    # FastAPI backend and AI analyzers
│   ├── ai/
│   ├── routers/
│   ├── models/
│   ├── main.py
│   └── requirements.txt
└── README.md
```

## Tech Stack

**Frontend**

- React
- Vite
- React Router
- Axios
- Framer Motion
- TensorFlow.js pose-detection package

**Backend**

- FastAPI
- SQLAlchemy
- SQLite
- MediaPipe
- OpenCV
- NumPy
- Pytest

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/KarthikBalaji-007/Unnati.git
cd Unnati
```

### 2. Start the backend

```bash
cd sports-assessment-backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Backend runs at:

```text
http://localhost:8000
```

Swagger UI:

```text
http://localhost:8000/docs
```

### 3. Start the frontend

Open a second terminal:

```bash
cd sports-assessment-frontend
npm install
npm run dev
```

Frontend runs at:

```text
http://localhost:5173
```

## Development Commands

Frontend:

```bash
npm run dev
npm run build
npm run preview
npm run lint
```

Backend:

```bash
uvicorn main:app --reload
pytest
```

## Notes

- Uploaded test videos and local database files are intentionally ignored from Git.
- Research material, reports, and generated documentation are not included in this repository.
- The backend model files are included because they are required for local AI analysis.

## License

This project is licensed under the terms included in the repository `LICENSE` file.
