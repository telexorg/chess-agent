import os
from enum import Enum
from dotenv import load_dotenv

load_dotenv()

class DeploymentTypes(Enum):
    BLOCKING = "blocking"
    STREAMING = "streaming"
    WEBHOOK = "webhook"

def str_to_bool(value: str) -> bool:
    return value.lower() in ("1", "true", "yes", "on") if value else False

CHESS_ENGINE_PATH = os.getenv("CHESS_ENGINE_PATH")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME")
MINIO_BUCKET_ACCESS_KEY = os.getenv("MINIO_BUCKET_ACCESS_KEY")
MINIO_BUKCET_SECRET_KEY = os.getenv("MINIO_BUKCET_SECRET_KEY")
DEPLOYMENT_TYPE=os.getenv("DEPLOYMENT_TYPE", DeploymentTypes.BLOCKING.value)
WITH_TELEX_EXTENSIONS=str_to_bool(os.getenv("WITH_TELEX_EXTENSIONS"))

PORT = int(os.getenv("PORT", 7000))

