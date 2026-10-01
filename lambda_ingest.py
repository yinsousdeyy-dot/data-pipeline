"""
Lambda function for data ingestion into S3.
This function is packaged into lambda_ingest.zip for deployment.
"""

import json
import logging
import boto3
import os
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')


def handler(event, context):
    """
    Lambda handler for data ingestion.
    
    Args:
        event: AWS Lambda event
        context: AWS Lambda context
    
    Returns:
        dict: Status response
    """
    s3_bucket = os.environ.get('S3_BUCKET')
    
    if not s3_bucket:
        logger.error("S3_BUCKET environment variable not set")
        return {
            'statusCode': 500,
            'body': json.dumps('S3_BUCKET environment variable not set')
        }
    
    try:
        # Example: Ingest mock order data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        key = f"orders/raw/orders_{timestamp}.json"
        
        # Sample payload
        payload = {
            "records": [
                {
                    "order_id": "ord-001",
                    "customer_id": 101,
                    "customer_email": "user1@example.com",
                    "amount": 99.99,
                    "status": "COMPLETED",
                    "order_timestamp": datetime.now().isoformat()
                }
            ]
        }
        
        # Upload to S3
        s3_client.put_object(
            Bucket=s3_bucket,
            Key=key,
            Body=json.dumps(payload),
            ContentType='application/json'
        )
        
        logger.info(f"Successfully ingested data to s3://{s3_bucket}/{key}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Data ingestion successful',
                's3_key': key,
                'bucket': s3_bucket
            })
        }
    
    except Exception as e:
        logger.error(f"Error during data ingestion: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }
