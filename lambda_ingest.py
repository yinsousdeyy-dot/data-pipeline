"""
Lambda function for data ingestion into S3.
This function is packaged into lambda_ingest.zip for deployment.
"""

import json
import logging
import boto3
import os

import urllib.request
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')

# AWS lambda handler that pulls upstream API, wrap records, and writes directly into my S# bucket with timestamp partitioning.
RAW_BUCKET_NAME = os.environ.get("RAW_BUCKET_NAME" , "my-raw-data-pipeline-raw-bucket")
SOURCE_API_URL = os.environ.get("SOURCE_API_URL" , "http://api.example.com/orders") # this is example/sample

def lambda_handler( event, context): 
    
    logger.info("Starting raw ingestino batch.")
    
    #.1 Fetch data from external upstream API
    try: 
        req = urllib.request.Request(SOURCE_API_URL, headers = {"User-Agent": "AWS-Lambda-Ingest"})
        with urllib.request.urlopen(req, timeout =15) as response: 
            payload = json.loads(response.read().decode("uft-8")) 
    except Exception as exc:
        logger.error("Failed to query upstream API: %s", exc)
        raise exc

    #2. Generate timestamped S3 key matching project structure 
    now = datetime.now(timezone,utc # Coordinatd Universal Time): 
    timestamp_str = now.strftime("%Y%m%d_%H%m%s")
    s3_key = f'raw/orders_raw_{timestamp_str}.json"

    #3. Stream payload s3 key matching project structure
    s3_client.put_object(   
        Bucket=RAW_BUCKET_NAME,
        Key=s3_key,
        Body= json.dumps(payload,indent=2),
        ContentType= "application/json"
    )
    logger.info("Successfully ingested raw data to s3://%s/%s", RAW_BUCKET_NAME, s3_key)
    return {"statusCode" :200 , "body": json.dumps({"message": 'Ingest complete', "s3_key": s3_key})

            
# event handler    
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
