import json
import os
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def build_response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Content-Type": "application/json"
        },
        "body": json.dumps(body)
    }

def send_email(event, context):
    try:
        body = json.loads(event['body'])
    except (TypeError, ValueError, KeyError) as e:
        logger.error(f"JSON parse error: {str(e)}")
        return build_response(400, {"error": "Invalid JSON format"})
    
    required_fields = ['receiver_email', 'subject', 'body_text']
    missing_fields = [field for field in required_fields if field not in body]
    
    if missing_fields:
        error_msg = f"Missing required fields: {', '.join(missing_fields)}"
        logger.error(error_msg)
        return build_response(400, {"error": error_msg})
    
    receiver_email = body['receiver_email']
    subject = body['subject']
    body_text = body['body_text']
    
    # Offline simulation
    if os.environ.get('IS_OFFLINE') == 'true':
        logger.info("OFFLINE MODE: Simulating email sending")
        logger.info(f"To: {receiver_email}")
        logger.info(f"Subject: {subject}")
        logger.info(f"Body: {body_text}")
        return build_response(200, {"message": "Email simulated successfully (offline mode)"})
    
    # AWS SES integration
    sender_email = os.environ['SENDER_EMAIL']
    
    try:
        ses = boto3.client('ses')
        response = ses.send_email(
            Source=sender_email,
            Destination={'ToAddresses': [receiver_email]},
            Message={
                'Subject': {'Data': subject},
                'Body': {'Text': {'Data': body_text}}}
        )            
        logger.info(f"Email sent! Message ID: {response['MessageId']}")
        return build_response(200, {"message": "Email sent successfully"})
    
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_msg = e.response['Error']['Message']
        logger.error(f"SES error ({error_code}): {error_msg}")
        status_code = 500 if error_code == 'InternalFailure' else 400
        return build_response(status_code, {"error": f"Email sending failed: {error_msg}"})
    
    except KeyError as e:
        logger.error(f"Configuration error: {str(e)}")
        return build_response(500, {"error": "Server configuration error"})