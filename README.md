# EcoMind AI – Intelligent Smart Waste & Circular Economy Platform

EcoMind AI extends the Smart Waste Management System into an AI-ready smart-city platform.

## Core modules
- AI waste image identification
- Personal environmental dashboard and eco points
- Smart-bin telemetry simulation with fill level, weight, battery and priority
- Waste-generation forecasting from recent activity
- What-if waste reduction simulator
- Environmental impact estimates
- Circular-economy reuse marketplace
- Disposal/recycling map and collection requests
- AI assistant and notifications
- Admin command center (enable with the Vercel ADMIN_EMAIL environment variable)

## Architecture
- Python 3 + Flask
- Flask-SQLAlchemy
- PostgreSQL/Neon in production, SQLite for local development
- Bootstrap, Chart.js and Leaflet
- Vercel-compatible Flask entry point

## New V2 flow
**Identify → Predict → Monitor → Collect → Reuse/Recycle → Reward → Measure Impact**

### IoT-ready design
The smart-bin module currently uses seeded telemetry so the project works without hardware. It is structured for future ESP32/ultrasonic/load-cell integration through the /api/smart-bins endpoint.

### Forecast note
The current forecast is a transparent baseline calculation from the user's last 7 days of recorded waste-identification activity. It is not presented as a trained ML prediction model.

### Impact note
Environmental impact values are project estimates based on configurable category factors. They are not direct carbon-accounting measurements.
