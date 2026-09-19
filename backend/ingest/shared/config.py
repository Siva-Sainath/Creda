import os

DATA_BUCKET = os.environ.get("DATA_BUCKET", "")
CASES_TABLE = os.environ.get("CASES_TABLE", "")
CASE_QUEUE_URL = os.environ.get("CASE_QUEUE_URL", "")
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-5-haiku-20241022-v1:0")
PATTERN_VERSION = os.environ.get("PATTERN_VERSION", "v1")
CURATED_PREFIX = os.environ.get("CURATED_PREFIX", "curated")
