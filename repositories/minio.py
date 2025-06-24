from minio import Minio
from repositories.env import MINIO_ENDPOINT, MINIO_BUCKET_ACCESS_KEY, MINIO_BUKCET_SECRET_KEY

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_BUCKET_ACCESS_KEY,
    secret_key=MINIO_BUKCET_SECRET_KEY,
)
