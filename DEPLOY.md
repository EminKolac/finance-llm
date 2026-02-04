# Cloud Deployment Guide

## Your BIST Stock Tickers
HALKB, TRENJ, TRMET, TRALT, TCELL, THYAO, TTKOM, TURSG, VAKBN, KRDMD

---

## Option 1: Railway (Recommended - Free tier available)

1. Go to https://railway.app and sign up with GitHub
2. Click "New Project" > "Deploy from GitHub repo"
3. Select your repository
4. Add environment variable:
   - `SECRET_KEY` = (generate a random string)
5. Deploy!

Your app will be live at: `https://your-app.up.railway.app`

---

## Option 2: Render (Free tier available)

1. Go to https://render.com and sign up
2. Click "New" > "Web Service"
3. Connect your GitHub repository
4. Settings:
   - Environment: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 web_app:app`
5. Add environment variable:
   - `SECRET_KEY` = (generate a random string)
6. Deploy!

---

## Option 3: Heroku

1. Install Heroku CLI: https://devcenter.heroku.com/articles/heroku-cli
2. Login and create app:
   ```bash
   heroku login
   heroku create your-app-name
   ```
3. Set environment variables:
   ```bash
   heroku config:set SECRET_KEY=your-random-secret-key
   ```
4. Deploy:
   ```bash
   git push heroku main
   ```

---

## Option 4: Docker (Any cloud with Docker support)

Build and run:
```bash
docker build -t finance-llm .
docker run -p 8080:8080 -e SECRET_KEY=your-secret finance-llm
```

Deploy to:
- Google Cloud Run
- AWS ECS/Fargate
- Azure Container Apps
- DigitalOcean App Platform

---

## Option 5: Fly.io

1. Install flyctl: https://fly.io/docs/hands-on/install-flyctl/
2. Login and launch:
   ```bash
   fly auth login
   fly launch
   ```
3. Set secrets:
   ```bash
   fly secrets set SECRET_KEY=your-random-secret-key
   ```
4. Deploy:
   ```bash
   fly deploy
   ```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| SECRET_KEY | Yes | Random string for session security |
| PORT | Auto | Set automatically by most platforms |

Note: OpenAI API key is entered by users in the web interface, not stored on server.

---

## Quick Test Locally

```bash
cd finance_llm
pip install -r requirements.txt
python web_app.py
```

Open http://localhost:5000
