import os
import streamlit as st
import uuid

def save_uploaded_file(uploaded_file, directory, filename=None):
    """
    Save an uploaded file to the specified directory
    
    Args:
        uploaded_file: The uploaded file from st.file_uploader
        directory: The directory to save the file to
        filename: Optional custom filename, if None, uses the original filename
        
    Returns:
        The path to the saved file
    """
    # Create directory if it doesn't exist
    os.makedirs(directory, exist_ok=True)
    
    # Generate filename if not provided
    if not filename:
        # Use original filename but add a UUID to avoid conflicts
        file_ext = os.path.splitext(uploaded_file.name)[1]
        filename = f"{uuid.uuid4().hex}{file_ext}"
    
    # Full path to save the file
    file_path = os.path.join(directory, filename)
    
    # Save the file
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return file_path

def get_file_extension(filename):
    """Get the extension of a file"""
    return os.path.splitext(filename)[1].lower()

def is_valid_file_type(filename, allowed_extensions):
    """Check if a file has an allowed extension"""
    return get_file_extension(filename) in allowed_extensions

def get_file_size_mb(uploaded_file):
    """Get the size of an uploaded file in MB"""
    return uploaded_file.size / (1024 * 1024)