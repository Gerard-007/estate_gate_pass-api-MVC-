import os
from mongoengine import connect


class Config:
    JWT_SECRET_KEY = "jwt_secret_key"
    FRONTEND_URL = "http://localhost:5000"


def initialize_db():
    MONGO_URI = "mongodb+srv://<username>:<password>@cluster0.tvycbjn.mongodb.net/<table-name>?retryWrites=true&w=majority"
    try:
        connect(host=MONGO_URI)
        print("Connected to MongoDB!")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        exit(1)
