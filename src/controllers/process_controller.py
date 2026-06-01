from .base_controller import BaseController
from .project_controller import ProjectController
import os
from langchain_community.document_loaders import TextLoader, PyMuPDFLoader
from models import ProcessingEnums
from typing import List
from dataclasses import dataclass
from utils.pdf_loader import pdf_loader

@dataclass
class Document:
    page_content: str
    metadata : dict

class ProcessController(BaseController):
    
    def __init__(self, project_id: str):
        super().__init__()
        
        self.project_id = project_id
        self.project_path = ProjectController().get_project_path(project_id)
        
    def get_file_extension(self, file_id: str):
        return os.path.splitext(file_id)[-1] # txt, pdf, doc
    
    def get_file_loader(self, file_id : str):
        """
        Choose file loader based file extension
        """
        
        file_ext = self.get_file_extension(file_id=file_id)
        file_path = os.path.join(       # Combine both project path and file id
            self.project_path,
            file_id
        )
        if not os.path.exists(file_path):
            return None
        
        if file_ext == ProcessingEnums.TXT.value:
            return TextLoader(file_path, encoding="utf-8")
        
        if file_ext == ProcessingEnums.PDF.value:
            return PyMuPDFLoader(file_path=file_path)
        
        return None
        
    def get_file_content(self, file_id:str):
        loader = self.get_file_loader(file_id=file_id)
        if loader :
            return loader.load()

        return None
    
    def process_file_content(self, file_content: list,
                             chunk_size: int=100, overlap_size: int=20):
        
        file_content_text = [
            rec.page_content
            for rec in file_content
        ]
        
        file_content_metadata = [
            rec.metadata
            for rec in file_content
        ]

        
        chunks = self.process_simpler_splitter(
            texts= file_content_text,
            metadatas=file_content_metadata,
            chunk_size=chunk_size,
        )
        
        return chunks
        
    def process_simpler_splitter(self, texts: List[str], metadatas: List[dict], chunk_size: int, splitter: str= "\n"):
        full_text = " ".join(texts)
        
        # Split by splitting tag
        lines = [ doc.strip() for doc in full_text.split(splitter) if len(doc.strip()) > 1 ]
        
        chunks = []
        current_chunk = ""
        
        for line in lines:
            current_chunk += line + splitter
            if len(current_chunk) >= chunk_size:
                chunks.append(Document(
                    page_content=current_chunk.strip(),
                    metadata={}
                ))
                
                current_chunk = ""
                
        if len(current_chunk) >= 0:
            chunks.append(Document(
                page_content=current_chunk.strip(),
                metadata={}
            ))
        
        return chunks