# Smart Waste Management System

AI-powered Flask web application for waste identification, classification, recycling guidance, collection requests, disposal-center mapping and EcoBuddy chatbot.

## Local setup
python -m venv venv
venv\\Scripts\\activate
pip install -r requirements.txt
python app.py

Open http://127.0.0.1:5000

## Vercel deployment
This project includes vercel.json and is configured as a Python serverless application. Import the GitHub repository into Vercel and deploy. Set SECRET_KEY as an environment variable in Vercel.

**Persistence note:** Vercel serverless storage is not persistent. The included SQLite database is suitable for local/demo use. For production, replace SQLite with a hosted PostgreSQL/MySQL database and use object storage for uploads.

The AI identifier currently uses a clearly labeled local demo classifier. Integrate TensorFlow/PyTorch/YOLO or a vision API for real model inference.
