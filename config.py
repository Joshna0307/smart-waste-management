import os
BASE_DIR=os.path.abspath(os.path.dirname(__file__))
class Config:
    SECRET_KEY=os.environ.get("SECRET_KEY","smart-waste-dev-key-change-me")
    SQLALCHEMY_DATABASE_URI="sqlite:///"+os.path.join(BASE_DIR,"database.db")
    SQLALCHEMY_TRACK_MODIFICATIONS=False
    MAX_CONTENT_LENGTH=8*1024*1024
    UPLOAD_FOLDER=os.path.join(BASE_DIR,"static","uploads")
    ALLOWED_EXTENSIONS={"png","jpg","jpeg","webp"}
