# Central Bot API

## Overview
Central Bot API server for managing distributed Twitter bots. Deploys to Heroku free tier.

## Features
- Device heartbeat monitoring
- Real-time command dispatch
- Fleet status monitoring
- Emergency controls
- Activity logging
- Performance analytics

## Deployment to Heroku

### Prerequisites
1. Heroku account (free)
2. Heroku CLI installed
3. Git installed

### Deploy Steps
```bash
# 1. Initialize git repo
git init
git add .
git commit -m "Initial Central Bot API"

# 2. Create Heroku app
heroku create your-twitter-central

# 3. Deploy
git push heroku main

# 4. Check logs
heroku logs --tail
```

## API Endpoints

### Device Communication
- `POST /api/device/<id>/heartbeat` - Device status updates
- `GET /api/device/<id>/commands` - Get pending commands
- `POST /api/device/<id>/activity` - Log completed activities

### Control Commands
- `POST /api/control/stop/<id>` - Stop specific device
- `POST /api/control/restart/<id>` - Restart specific device
- `POST /api/control/emergency_stop_all` - Emergency stop all devices

### Monitoring
- `GET /api/status/all` - Complete fleet status
- `GET /api/status/analytics` - Aggregated analytics
- `GET /health` - Health check

## Testing
```bash
# Test basic connectivity
curl https://your-app.herokuapp.com/

# Test health check
curl https://your-app.herokuapp.com/health

# Send test heartbeat
curl -X POST https://your-app.herokuapp.com/api/device/test_device/heartbeat \
  -H "Content-Type: application/json" \
  -d '{"uptime_hours": 1, "actions_today": {"tweets": 5}}'
```

## Environment
- Python 3.10.8
- Flask web framework
- Gunicorn WSGI server
- Heroku cloud platform

