from io import BytesIO
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_migrate import Migrate
from flask_cors import CORS
from models import db, bcrypt, User, Chat, Message
from datetime import timedelta
from config import Config
from utils import upload_file_to_s3, extract_text_from_pdf, deploy_to_s3, call_lambda_function
import requests
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)

CORS(app)

db.init_app(app)
bcrypt.init_app(app)
jwt = JWTManager(app)
migrate = Migrate(app, db)

@app.route('/check', methods=['get'])
def check():
    return 200

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    logger.info("Received signup request")
    data = request.json
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if User.query.filter_by(email=email).first():
        logger.warning(f"Signup failed: Email {email} already exists")
        return jsonify({'error': 'Email already exists'}), 409

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    user = User(name=name, email=email, password=hashed_password)
    db.session.add(user)
    db.session.commit()

    logger.info(f"User {email} signed up successfully")
    
    expires = timedelta(days=15)
    access_token = create_access_token(identity={'email': user.email}, expires_delta=expires)
    return jsonify({'token': access_token}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    logger.info("Received login request")
    data = request.json
    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()
    if user and bcrypt.check_password_hash(user.password, password):
        logger.info(f"User {email} logged in successfully")
        
        expires = timedelta(days=15)
        access_token = create_access_token(identity={'email': user.email}, expires_delta=expires)
        return jsonify({'token': access_token}), 200

    logger.warning(f"Login failed for email {email}")
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/auth/user', methods=['GET'])
@jwt_required()
def get_current_user():
    try:
        logger.info("Fetching current user information")
        
        # Get the current user's identity (email) from the JWT token
        current_user = get_jwt_identity()
        
        # Query the user from the database using the email
        user = User.query.filter_by(email=current_user['email']).first()
        
        if not user:
            # Return an error if the user is not found
            logger.warning(f"User not found: {current_user['email']}")
            return jsonify({'error': 'User not found'}), 404

        # Return the user's information as JSON
        user_info = {
            'id': user.id,
            'name': user.name,
            'email': user.email
        }

        logger.info(f"User information fetched: {user_info}")
        return jsonify({'user': user_info}), 200

    except Exception as e:
        # Catch any exception and return an error response
        logger.error(f"Error fetching user information: {str(e)}")
        return jsonify({'error': 'An error occurred while fetching user information'}), 500

@app.route('/api/chats', methods=['POST'])
@jwt_required()
def create_chat():
    logger.info("Received create chat request")
    current_user = get_jwt_identity()
    user = User.query.filter_by(email=current_user['email']).first()

    title = request.form.get('title')
    additional_description = request.form.get('additionalDescription')
    resume = request.files['resume']

    if not title or not resume:
        logger.warning("Chat creation failed: Missing required fields")
        return jsonify({'error': 'Missing required fields'}), 400

    resume_filename = resume.filename
    resume_file = resume.read()  # Read the file content directly

    # Extract text from PDF for initial prompt
    resume_text = extract_text_from_pdf(resume_file)

    # Upload resume to S3 and get URL
    resume_url = upload_file_to_s3(resume_text, user.id, resume_filename) 
    if not resume_url:
        logger.error("Failed to upload resume to S3")
        return jsonify({'error': 'Failed to upload resume'}), 500

    # Create the chat entry in the database
    chat = Chat(
        title=title,
        additional_description=additional_description,
        resume_url=resume_url,
        user=user,
        page_url=""
    )
    db.session.add(chat)
    db.session.commit()
    logger.info(f"Chat {chat.id} created for user {user.email}")

    # Prepare initial prompt
    initial_prompt = (
        "Using my resume, generate a static HTML and CSS portfolio page with a good-looking UI and CSS. "
        "Only provide the code, no explanations or other text. Keep everything in a single file (index.html) "
        "and use internal CSS and JS.\n"
        f"Additional Description: {additional_description}\n\n"
        f"Resume Text:\n{resume_text}"
    )
    initial_response = call_lambda_function(initial_prompt, resume_url)

    # Store the initial response as a message
    bot_message = Message(sender='bot', text=initial_response, chat=chat)
    db.session.add(bot_message)
    db.session.commit()

    logger.info(f"Initial response stored in chat {chat.id}: {initial_response}")
    return jsonify({
        'chat': {
            'id': chat.id,
            'title': chat.title,
            'page_url': '',
            'initialMessage': {
                'sender': 'bot',
                'text': initial_response
            },
            'messages': [
                {
                    'sender': 'bot',
                    'text': initial_response,
                    'time': bot_message.timestamp
                }
            ]
        }
    }), 201

@app.route('/api/chats/<int:chat_id>/messages', methods=['POST'])
@jwt_required()
def send_message(chat_id):
    data = request.json
    user_message = data.get('message')
    current_user = get_jwt_identity()

    logger.info(f"Received message for chat {chat_id} from user {current_user['email']}")

    user = User.query.filter_by(email=current_user['email']).first()
    chat = Chat.query.get_or_404(chat_id)

    if chat.user_id != user.id:
        logger.warning(f"Unauthorized access attempt by user {user.email} for chat {chat_id}")
        return jsonify({'error': 'Unauthorized access'}), 403

    # Save user message
    message = Message(sender='user', text=user_message, chat=chat)
    db.session.add(message)
    db.session.commit()
    logger.info(f"User message stored in chat {chat_id}: {user_message}")
    
    all_messages = Message.query.filter_by(chat_id=chat.id).order_by(Message.timestamp).all()
    
    # Build the conversation context
    conversation_context = ''
    for msg in all_messages:
        conversation_context += f"{msg.sender}: {msg.text}\n"

    # Add user message to the context
    conversation_context += f"user: {user_message}\n"

    # Generate response with full context
    prompt = (
        f"{conversation_context}\n"
        "Using my resume, generate a static HTML and CSS portfolio page with a good-looking UI and CSS. "
        "Only provide the code, no explanations or other text. Keep everything in a single file (index.html) "
        "and use internal CSS and JS."
    )
    
    response_text = call_lambda_function(prompt, chat.resume_url)

    # Save bot message
    bot_message = Message(sender='bot', text=response_text, chat=chat)
    db.session.add(bot_message)
    db.session.commit()

    logger.info(f"Bot response stored in chat {chat_id}: {response_text}")
    
    # Return the new message to the client
    return jsonify({
        'message': {
            'sender': 'bot',
            'text': response_text,
            'time': bot_message.timestamp
        }
    }), 201

@app.route('/api/chats', methods=['GET'])
@jwt_required()
def get_chats():
    logger.info("Fetching chats for current user")
    current_user = get_jwt_identity()
    user = User.query.filter_by(email=current_user['email']).first()

    chats = Chat.query.filter_by(user_id=user.id).all()
    logger.info(f"Found {len(chats)} chats for user {user.email}")
    return jsonify({'chats': [{'id': chat.id, 'title': chat.title, 'page_url': chat.page_url, 'lastMessage': chat.messages[-1].text if chat.messages else '', 'lastUpdated': chat.messages[-1].timestamp if chat.messages else ''} for chat in chats]}), 200

@app.route('/api/chats/<int:chat_id>/messages', methods=['GET'])
@jwt_required()
def get_chat_messages(chat_id):
    logger.info(f"Fetching messages for chat {chat_id}")
    current_user = get_jwt_identity()
    user = User.query.filter_by(email=current_user['email']).first()

    chat = Chat.query.get_or_404(chat_id)
    if chat.user_id != user.id:
        logger.warning(f"Unauthorized access attempt by user {user.email} for chat {chat_id}")
        return jsonify({'error': 'Unauthorized access'}), 403

    messages = Message.query.filter_by(chat_id=chat.id).order_by(Message.timestamp).all()
    logger.info(f"Found {len(messages)} messages for chat {chat_id}")
    return jsonify({'messages': [{'sender': message.sender, 'text': message.text, 'time': message.timestamp} for message in messages]}), 200

@app.route('/api/deploy', methods=['POST'])
@jwt_required()
def deploy_chat():
    data = request.json
    chat_id = data.get('chat_id')
    content = data.get('content')

    if not chat_id or not content:
        return jsonify({'error': 'Chat ID and content are required'}), 400

    current_user = get_jwt_identity()
    user = User.query.filter_by(email=current_user['email']).first()
    
    logger.info(f"Received deployment request for chat {chat_id} from user {user.id}")

    # Define S3 file path
    s3_file_path = f"pages/{user.id}/pages-{chat_id}/index.html"
    
    logger.info(f"s3_file_path: {s3_file_path}")

    # Deploy content to S3
    s3_url = deploy_to_s3(content, s3_file_path)

    # Update chat with page_url
    chat = Chat.query.get(chat_id)
    if not chat:
        return jsonify({'error': 'Chat not found'}), 404

    chat.page_url = s3_url
    db.session.commit()

    return jsonify({'page_url': s3_url}), 200

if __name__ == '__main__':
    logger.info("Starting Flask application")
    app.run(host=app.config['FLASK_RUN_HOST'], port=int(app.config['FLASK_RUN_PORT']), debug=True)
