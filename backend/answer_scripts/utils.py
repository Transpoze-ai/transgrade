import boto3
from PIL import Image
from django.conf import settings
from botocore.exceptions import ClientError


def get_s3_client():
    return boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME
    )


def upload_image_to_s3(image_file, s3_key, content_type='image/jpeg'):
    try:
        s3_client = get_s3_client()
        s3_client.upload_fileobj(
            image_file,
            settings.AWS_S3_BUCKET_NAME,
            s3_key,
            ExtraArgs={
                'ContentType': content_type,
                'ACL': 'public-read'
            }
        )
        return True, None
    except ClientError as e:
        return False, str(e)


def delete_s3_folder(folder_path):
    try:
        s3_client = get_s3_client()
        response = s3_client.list_objects_v2(
            Bucket=settings.AWS_S3_BUCKET_NAME,
            Prefix=folder_path
        )
        
        if 'Contents' in response:
            objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
            s3_client.delete_objects(
                Bucket=settings.AWS_S3_BUCKET_NAME,
                Delete={'Objects': objects_to_delete}
            )
        return True, None
    except ClientError as e:
        return False, str(e)


def process_and_upload_images(roll_no, question_paper_uuid, image_files):
    folder_path = f"answer-images/{question_paper_uuid}/{roll_no}/"
    image_urls = []
    
    for i, image_file in enumerate(image_files):
        try:
            img = Image.open(image_file)
            
            format_to_ext = {
                'JPEG': '.jpg',
                'PNG': '.png',
                'TIFF': '.tiff',
                'BMP': '.bmp'
            }
            ext = format_to_ext.get(img.format, '.jpg')
            content_type = f"image/{img.format.lower()}" if img.format.lower() != 'jpeg' else 'image/jpeg'
            
            filename = f"image_{i+1:03d}{ext}"
            s3_key = folder_path + filename
            
            image_file.seek(0)
            success, error = upload_image_to_s3(image_file, s3_key, content_type)
            if not success:
                raise Exception(f"Failed to upload {filename}: {error}")
            
            s3_url = f"https://{settings.AWS_S3_CUSTOM_DOMAIN}/{s3_key}"
            image_urls.append(s3_url)
            
        except Exception as e:
            # Cleanup uploaded images on error
            for uploaded_url in image_urls:
                s3_key_to_delete = uploaded_url.replace(f"https://{settings.AWS_S3_CUSTOM_DOMAIN}/", "")
                delete_image_from_s3(s3_key_to_delete)
            raise ValueError(f"Error processing image {i}: {str(e)}")
    
    return image_urls


def delete_image_from_s3(s3_key):
    try:
        s3_client = get_s3_client()
        s3_client.delete_object(
            Bucket=settings.AWS_S3_BUCKET_NAME,
            Key=s3_key
        )
        return True, None
    except ClientError as e:
        return False, str(e)


def validate_image_file(image_file, max_size_mb=5):
    try:
        # Check file size
        image_file.seek(0, 2)
        file_size = image_file.tell()
        image_file.seek(0)
        
        if file_size > max_size_mb * 1024 * 1024:
            return False, f"Image too large (max {max_size_mb}MB)"
        
        # Validate image format
        img = Image.open(image_file)
        img.verify()
        image_file.seek(0)
        
        return True, None
        
    except Exception as e:
        return False, str(e)