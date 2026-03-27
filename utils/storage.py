import cloudinary
import cloudinary.uploader
import cloudinary.api
import os
import logging

# Configure Cloudinary
# This relies on the environment variables being loaded by the main app
if os.getenv("CLOUDINARY_URL"):
    cloudinary.config(cloudinary_url=os.getenv("CLOUDINARY_URL"))
else:
    cloudinary.config(
        cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
        api_key=os.getenv("CLOUDINARY_API_KEY"),
        api_secret=os.getenv("CLOUDINARY_API_SECRET")
    )

def upload_evidence_to_cloudinary(file_path, user_id, file_name):
    """
    Uploads a file to Cloudinary, placing it in a 'locker' folder.

    Args:
        file_path (str): The local path to the file to upload.
        user_id (str): The ID of the user to associate with the file.
        file_name (str): The original name of the file.

    Returns:
        dict: The result of the upload from Cloudinary.
    """
    try:
        # The public_id determines the name of the file in Cloudinary.
        # We construct it to be unique and organized.
        public_id = f"{user_id}/{file_name}"

        # Upload the file to the 'locker' folder
        result = cloudinary.uploader.upload(
            file_path,
            folder="locker",
            public_id=public_id,
            resource_type="auto"  # Automatically detect if it's an image, video, or raw file
        )
        return result
    except Exception as e:
        logging.error(f"Error uploading to Cloudinary: {e}")
        return None
