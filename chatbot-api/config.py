from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI')
    DATABASE_URI = os.getenv('DATABASE_URI')
    SQLALCHEMY_TRACK_MODIFICATIONS = os.getenv('SQLALCHEMY_TRACK_MODIFICATIONS') == 'True'
    DB_HOST=os.getenv('DB_HOST')
    DB_USER=os.getenv('DB_USER')
    DB_PASSWORD=os.getenv('DB_PASSWORD')
    DB_NAME=os.getenv('DB_NAME')
    
    FLASK_APP = os.getenv('FLASK_APP')
    FLASK_ENV = os.getenv('FLASK_ENV')
    FLASK_RUN_HOST = os.getenv('FLASK_RUN_HOST')
    FLASK_RUN_PORT = os.getenv('FLASK_RUN_PORT')
    
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_S3_BUCKET_NAME = os.getenv('AWS_S3_BUCKET_NAME')
    AWS_REGION = os.getenv('AWS_REGION')
    AWS_SESSION_TOKEN = os.getenv('AWS_SESSION_TOKEN')
    
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_INSTRUCTIONS = os.getenv('OPENAI_INSTRUCTIONS')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
