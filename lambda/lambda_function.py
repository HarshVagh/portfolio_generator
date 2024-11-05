import os
import boto3
import json
from openai import OpenAI

def get_secret(secret_name, aws_access_key, aws_secret_key, aws_session_token):
    secrets_client = boto3.client(
        'secretsmanager',
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        region_name="us-east-1",
        aws_session_token=aws_session_token
    )

    response = secrets_client.get_secret_value(SecretId=secret_name)
    secret = json.loads(response['SecretString'])
    return secret

def get_text_from_s3(bucket_name, key_name, aws_access_key, aws_secret_key, aws_session_token):
    s3_client = boto3.client(
        's3',
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        region_name="us-east-1",
        aws_session_token=aws_session_token
    )

    response = s3_client.get_object(Bucket=bucket_name, Key=key_name)
    text_content = response['Body'].read().decode('utf-8')
    return text_content

def lambda_handler(event, context):
    try:
        # Retrieve environment variables
        secret_name = os.environ['SECRETS_ARN']
        aws_access_key = os.environ['KEY_ID']
        aws_secret_key = os.environ['ACCESS_KEY']
        aws_session_token = os.environ['TOKEN']

        # Retrieve the secrets
        secrets = get_secret(secret_name, aws_access_key, aws_secret_key, aws_session_token)
        
        prompt = event.get('prompt', '')
        resume_url = event.get('resume_url', '')
        
        # Extract bucket name and key from the URL
        parsed_url = resume_url.replace("https://", "").split('.s3.amazonaws.com/')
        bucket_name = parsed_url[0]
        key_name = parsed_url[1]

        # Retrieve text content from S3
        text_content = get_text_from_s3(bucket_name, key_name, aws_access_key, aws_secret_key, aws_session_token)
        
        # Prepare the full prompt
        full_prompt = (
            f"{prompt}\n\nAccess and Extract text from my resume for information "
            f"about my portfolio.\n\n Here is an AWS S3 public link to my resume: \n"
            f"---------------------\n{text_content}"
        )
        
        # Initialize OpenAI client
        client = OpenAI(api_key=secrets['OPENAI_API_KEY'])
        
        # Create messages for the ChatGPT API
        messages = [
            {"role": "system", "content": secrets['OPENAI_INSTRUCTIONS']},
            {"role": "user", "content": full_prompt}
        ]
        
        # Call the OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )
        
        return {
            'statusCode': 200,
            'body': response.choices[0].message.content.strip()
        }

    except Exception as e:
        print(f"Error while calling ChatGPT API: {e}")
        return {
            'statusCode': 500,
            'body': "An error occurred while processing the request."
        }
