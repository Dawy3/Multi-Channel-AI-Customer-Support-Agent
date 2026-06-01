"""
Files that controll data Uploading like(Validation, Unique path, clear name if it had ambigous name EX: @assets$$$$.. )
"""

from .base_controller import BaseController
from fastapi import UploadFile
from models import ResponseSignals
from .project_controller import ProjectController
import os
import re

class DataController(BaseController):
    
    def __init__(self):
        super().__init__()
        self.size_scale = 1048576                # Convert MB to Bytes 
        
    def validate_uploaded_file(self, file: UploadFile):
        """Validate the file if it's wrong type or excceded size"""
        
       # Wrong file type
        if file.content_type not in self.app_settings.FILE_ALLOWED_TYPES:
            return ResponseSignals.FILE_TYPE_NOT_SUPPORTED.value
        
        # Exceeded file size
        if file.size > self.app_settings.FILE_MAX_SIZE * self.size_scale:
            return ResponseSignals.FILE_SIZE_EXCEEDED
        
        return True, ResponseSignals.FILE_VALIDATED_SUCCESS.value
    
    def generate_unique_filepath(self, orig_file_name: str, project_id):
        """Generate unqiue filename with project id in case uploading the same file"""
        
        random_key = self.generate_random_string()                          # will generate random string and numbers 
        project_path = ProjectController().get_project_path(project_id)     # Create a folder that Based on project path EX: ./assets/files/{project_id}
        
        
        cleaned_file_name = self._get_cleaned_filename(orig_file_name=orig_file_name)   # cleaned file name wether have underscore dash etc...
        
        # Combine all together
        new_file_path = os.path.join(
            project_path,                           # ./assets/files/{project_id}
            random_key + "_" + cleaned_file_name    # EX: szxr8402_file.pdf
        )
        
        # If the user upload existing file path then generate new random key.
        while os.path.exists(new_file_path):
            random_key = self.generate_random_string()
            new_file_path = os.path.join(
                project_path,
                random_key + "_" + cleaned_file_name
            )
        
        return new_file_path, random_key + "_" + cleaned_file_name      # EX: ./assets/files/1/szxr8402_file.pdf
    
    def _get_cleaned_filename(self, orig_file_name: str):
        
        # Remove any special characters except underscore and dot
        cleaned_filename = re.sub(r'[^\w.]', '' , orig_file_name.strip())
        
        # Replace space with underscore
        cleaned_filename = cleaned_filename.replace(" ", "_")
        
        return cleaned_filename
    
    