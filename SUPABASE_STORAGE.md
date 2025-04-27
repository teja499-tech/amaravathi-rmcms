# Supabase Storage Setup Guide

This guide explains how to set up Supabase Storage for file uploads in the Amaravathi RMBMP application.

## Prerequisites

1. A Supabase account and project - See [SUPABASE_SETUP.md](SUPABASE_SETUP.md) if you haven't created one yet.
2. The Amaravathi RMBMP application codebase.

## Steps to Configure Supabase Storage

### 1. Create a Storage Bucket

1. Log in to your Supabase Dashboard.
2. Select your project.
3. Navigate to "Storage" in the left sidebar.
4. Click on "Create a new bucket".
5. Enter the bucket name (e.g., `amaravathi-files`).
6. Choose the appropriate access level:
   - **Private**: Files are only accessible via authenticated API requests.
   - **Public**: Files are publicly accessible via URL.
7. Click "Create bucket".

### 2. Configure Bucket Permissions

1. Once the bucket is created, click on it to view its details.
2. Go to the "Policies" tab.
3. Configure access policies:
   - Create a policy to allow authenticated users to upload files.
   - Create a policy to allow authenticated users to read files.
   - Optionally, create a policy to allow file deletion.

Here are some example policies:

**For file uploads (INSERT):**
```sql
CREATE POLICY "Allow authenticated users to upload files"
ON storage.objects
FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'amaravathi-files');
```

**For file reading (SELECT):**
```sql
CREATE POLICY "Allow authenticated users to read files"
ON storage.objects
FOR SELECT
TO authenticated
USING (bucket_id = 'amaravathi-files');
```

**For file deletion (DELETE):**
```sql
CREATE POLICY "Allow authenticated users to delete their own files"
ON storage.objects
FOR DELETE
TO authenticated
USING (bucket_id = 'amaravathi-files');
```

### 3. Update Environment Variables

1. Add the following variables to your `.env` file:
   ```
   SUPABASE_URL=https://your-project-id.supabase.co
   SUPABASE_KEY=your-supabase-anon-key
   SUPABASE_BUCKET=amaravathi-files
   ```

2. To find your values:
   - **SUPABASE_URL**: In your Supabase dashboard, go to Project Settings > API > URL
   - **SUPABASE_KEY**: In your Supabase dashboard, go to Project Settings > API > `anon` `public` key
   - **SUPABASE_BUCKET**: The name of the bucket you created

### 4. Using Supabase Storage in Your Application

The application already includes helper functions in `apps/core/utils/storage.py`:

- `upload_to_supabase(file, bucket, folder)`: Upload a file to Supabase Storage
- `get_file_from_supabase(path, bucket)`: Get a file URL from Supabase Storage
- `delete_file_from_supabase(path, bucket)`: Delete a file from Supabase Storage

To use these functions in your models:

```python
from apps.core.utils.storage import upload_to_supabase

# Example: Uploading a file
def upload_invoice(request):
    file = request.FILES.get('invoice')
    if file:
        result = upload_to_supabase(
            file=file,
            folder='invoices'  # Optional subfolder
        )
        
        if result.get('success'):
            # Store the file path and URL
            file_path = result.get('path')
            file_url = result.get('public_url')
```

### 5. Testing Uploads

1. Visit `/suppliers/test-upload/` in your application.
2. Use the form to upload a test file.
3. Verify that the file appears in your Supabase Storage bucket.

## Troubleshooting

- **Unauthorized Error**: Check your Supabase credentials in the `.env` file.
- **Permission Denied**: Review your bucket policies in Supabase.
- **Missing Bucket**: Ensure the bucket name in your `.env` matches the one in Supabase.

## Production Considerations

1. **Security**: For production, consider using signed URLs with expiration for sensitive files.
2. **File Size Limits**: Default maximum file size in Supabase is 50MB. Configure accordingly.
3. **Content Types**: Restrict allowed file types using bucket policies if needed. 