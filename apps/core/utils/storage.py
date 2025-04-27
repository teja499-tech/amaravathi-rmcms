import os
import uuid
from typing import Optional, Union, BinaryIO
import logging
from datetime import datetime

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from supabase import create_client, Client

logger = logging.getLogger(__name__)

def get_supabase_client() -> Client:
    """
    Creates and returns a Supabase client instance.
    
    Returns:
        Client: A Supabase client instance.
    """
    url = os.environ.get('SUPABASE_URL')
    key = os.environ.get('SUPABASE_KEY')
    
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
    
    return create_client(url, key)

def upload_to_supabase(
    file: Union[UploadedFile, BinaryIO], 
    bucket: Optional[str] = None, 
    folder: Optional[str] = None
) -> dict:
    """
    Uploads a file to Supabase Storage.
    
    Args:
        file: The file to upload (Django UploadedFile or file-like object)
        bucket: The storage bucket name (defaults to SUPABASE_BUCKET from env)
        folder: Optional folder path within the bucket
        
    Returns:
        dict: Response data containing file information
        
    Raises:
        ValueError: If bucket is not specified and not in environment variables
        Exception: For any upload errors
    """
    try:
        # Get bucket name from parameters or environment
        bucket_name = bucket or os.environ.get('SUPABASE_BUCKET')
        if not bucket_name:
            raise ValueError("Bucket name must be provided or set as SUPABASE_BUCKET in environment variables")
        
        # Get the Supabase client
        supabase = get_supabase_client()
        
        # Generate a unique filename to avoid conflicts
        original_name = getattr(file, 'name', 'file')
        file_extension = os.path.splitext(original_name)[1].lower()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        filename = f"{timestamp}_{unique_id}{file_extension}"
        
        # Construct the path with folder if provided
        path = f"{folder}/{filename}" if folder else filename
        
        # Upload the file to Supabase Storage
        if isinstance(file, UploadedFile):
            # For Django UploadedFile, we need to read the content
            file_content = file.read()
            
            # Reset file position for potential future reads
            file.seek(0)
        else:
            # For file-like objects
            file_content = file.read()
            
            # Reset file position
            try:
                file.seek(0)
            except:
                # Some file-like objects might not support seek
                pass
        
        # Upload to Supabase
        response = supabase.storage.from_(bucket_name).upload(
            path=path,
            file=file_content,
            file_options={"content-type": getattr(file, 'content_type', 'application/octet-stream')}
        )
        
        # Generate the public URL for the file
        public_url = supabase.storage.from_(bucket_name).get_public_url(path)
        
        return {
            "success": True,
            "path": path,
            "filename": filename,
            "public_url": public_url,
            "response": response
        }
        
    except Exception as e:
        logger.error(f"Failed to upload file to Supabase Storage: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def get_file_from_supabase(path: str, bucket: Optional[str] = None) -> dict:
    """
    Gets file information and download URL from Supabase Storage.
    
    Args:
        path: The file path within the bucket
        bucket: The storage bucket name (defaults to SUPABASE_BUCKET from env)
        
    Returns:
        dict: Response data containing file URL
    """
    try:
        # Get bucket name from parameters or environment
        bucket_name = bucket or os.environ.get('SUPABASE_BUCKET')
        if not bucket_name:
            raise ValueError("Bucket name must be provided or set as SUPABASE_BUCKET in environment variables")
        
        # Get the Supabase client
        supabase = get_supabase_client()
        
        # Generate a public URL for the file
        public_url = supabase.storage.from_(bucket_name).get_public_url(path)
        
        return {
            "success": True,
            "public_url": public_url
        }
        
    except Exception as e:
        logger.error(f"Failed to get file from Supabase Storage: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def delete_file_from_supabase(path: str, bucket: Optional[str] = None) -> dict:
    """
    Deletes a file from Supabase Storage.
    
    Args:
        path: The file path within the bucket
        bucket: The storage bucket name (defaults to SUPABASE_BUCKET from env)
        
    Returns:
        dict: Response data indicating success or failure
    """
    try:
        # Get bucket name from parameters or environment
        bucket_name = bucket or os.environ.get('SUPABASE_BUCKET')
        if not bucket_name:
            raise ValueError("Bucket name must be provided or set as SUPABASE_BUCKET in environment variables")
        
        # Get the Supabase client
        supabase = get_supabase_client()
        
        # Delete the file
        response = supabase.storage.from_(bucket_name).remove([path])
        
        return {
            "success": True,
            "response": response
        }
        
    except Exception as e:
        logger.error(f"Failed to delete file from Supabase Storage: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        } 