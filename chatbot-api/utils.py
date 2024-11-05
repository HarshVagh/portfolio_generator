# from openai import OpenAI
from flask import current_app
from botocore.exceptions import NoCredentialsError, ClientError
from PyPDF2 import PdfReader
from io import BytesIO, StringIO
import boto3
import json

def upload_file_to_s3(text_content, user_id, filename):
    try:
        # Initialize a session using Amazon S3
        s3_client = boto3.client(
            's3',
            aws_access_key_id=current_app.config['AWS_ACCESS_KEY_ID'],
            aws_secret_access_key=current_app.config['AWS_SECRET_ACCESS_KEY'],
            region_name=current_app.config['AWS_REGION'],
            aws_session_token=current_app.config.get('AWS_SESSION_TOKEN')
        )
        
        text_stream = StringIO(text_content)

        # Define the file path in S3
        s3_file_path = f"resumes/{user_id}/{filename}"

        # Upload the file to S3
        
        s3_client.put_object(
			Bucket=current_app.config['AWS_S3_BUCKET_NAME'],
			Key=s3_file_path,
			Body=text_stream.getvalue(),
			ContentType='text/plain'
		)

        # Create a URL for the uploaded file
        file_url = f"https://{current_app.config['AWS_S3_BUCKET_NAME']}.s3.amazonaws.com/{s3_file_path}"
        return file_url
    except NoCredentialsError:
        print("Credentials not available")
        return None
    except ClientError as e:
        print(f"Error occurred: {e}")
        return None
    
def deploy_to_s3(content, s3_key):
    # Initialize boto3 client
    s3 = boto3.client(
        's3',
        aws_access_key_id=current_app.config['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=current_app.config['AWS_SECRET_ACCESS_KEY'],
        region_name=current_app.config['AWS_REGION'],
        aws_session_token=current_app.config.get('AWS_SESSION_TOKEN')
    )

    # Get the S3 bucket name from environment variables
    bucket_name = current_app.config['AWS_S3_BUCKET_NAME']

    # Upload content directly as a binary stream
    s3.upload_fileobj(
        BytesIO(content.encode('utf-8')),
        bucket_name,
        s3_key,
        ExtraArgs={'ContentType': 'text/html'}
    )

    # Generate S3 URL for the uploaded file
    s3_url = f"https://{bucket_name}.s3.amazonaws.com/{s3_key}"
    return s3_url

def extract_text_from_pdf(file_bytes):
    reader = PdfReader(BytesIO(file_bytes))
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

def call_lambda_function(prompt, resume_url):
        lambda_client = boto3.client(
            'lambda',
            aws_access_key_id=current_app.config['AWS_ACCESS_KEY_ID'],
            aws_secret_access_key=current_app.config['AWS_SECRET_ACCESS_KEY'],
            region_name=current_app.config['AWS_REGION'],
            aws_session_token=current_app.config.get('AWS_SESSION_TOKEN')
        )
        payload = {
            'prompt': prompt,
            'resume_url': resume_url
        }
        json_payload = json.dumps(payload)
        response = lambda_client.invoke(
            FunctionName='ChatGPTPortfolioGenerator',
            InvocationType='RequestResponse',
            Payload=json_payload
        )
        response_payload = json.load(response['Payload'])
        return response_payload.get('body', 'No body in response')
    
def get_text_from_s3(s3_url):
    parsed_url = s3_url.replace("https://", "").split('.s3.amazonaws.com/')
    bucket_name = parsed_url[0]
    object_key = parsed_url[1]

    # Initialize the S3 client
    s3_client = boto3.client(
		's3',
		aws_access_key_id=current_app.config['AWS_ACCESS_KEY_ID'],
		aws_secret_access_key=current_app.config['AWS_SECRET_ACCESS_KEY'],
		region_name=current_app.config['AWS_REGION'],
		aws_session_token=current_app.config.get('AWS_SESSION_TOKEN')
	)
    
    # Fetch the object
    response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
    # Read the content
    text_content = response['Body'].read().decode('utf-8')
    
    return text_content
