# EVA Backend

## Setup

### 1. Create virtual environment
```bash
python -m venv .venv
```

### 2. Activate virtual environment
**Windows:**
```bash
.\.venv\Scripts\Activate.ps1
```

**Linux/Mac:**
```bash
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment
Copy `.env.example` to `.env` and fill in your API keys:
```bash
cp .env.example .env
```

## Running the server

```bash
python -m uvicorn app.main:app --reload
```

Or simply run:
```bash
python app/main.py
```

The API will be available at `http://localhost:8000`

### API Documentation
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

### Chat
- `POST /api/v1/chat/message` - Send a chat message
- `GET /api/v1/chat/health` - Health check for chat service

### Health
- `GET /api/v1/health` - Main health check
- `GET /api/v1/` - Root endpoint
