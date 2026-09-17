"""
Creates the creda-cases-local DynamoDB table on the local DynamoDB instance.
Run this ONCE after starting the DynamoDB Local docker container.

Usage:
  python scripts/setup_local_dynamo.py
"""
import boto3

dynamo = boto3.resource(
    "dynamodb",
    region_name="us-east-1",
    endpoint_url="http://localhost:8000",
    aws_access_key_id="local",
    aws_secret_access_key="local",
)

TABLE_NAME = "creda-cases-local"

# Delete existing table if present (clean slate)
try:
    dynamo.Table(TABLE_NAME).delete()
    print(f"Deleted existing table: {TABLE_NAME}")
except Exception:
    pass

table = dynamo.create_table(
    TableName=TABLE_NAME,
    BillingMode="PAY_PER_REQUEST",
    AttributeDefinitions=[
        {"AttributeName": "PK", "AttributeType": "S"},
        {"AttributeName": "SK", "AttributeType": "S"},
    ],
    KeySchema=[
        {"AttributeName": "PK", "KeyType": "HASH"},
        {"AttributeName": "SK", "KeyType": "RANGE"},
    ],
)

table.wait_until_exists()
print(f"[OK] Table created: {TABLE_NAME}")
print(f"     Endpoint: http://localhost:8000")
print()
print("Next step: run 'sam build' then 'sam local start-api' from the infra/ folder")
