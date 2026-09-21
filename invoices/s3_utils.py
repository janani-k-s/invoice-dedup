import boto3
from django.conf import settings


def get_s3_client():
    return boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )


def upload_file_to_s3(file_obj, key):
    """
    Uploads a file object to S3 under the given key (path/filename).
    Returns the S3 key on success.
    """
    s3 = get_s3_client()
    s3.upload_fileobj(file_obj, settings.AWS_S3_BUCKET_NAME, key)
    return key