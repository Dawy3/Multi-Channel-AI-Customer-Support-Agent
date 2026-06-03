from stores.llm.llm_interface import LLMInterface
from stores.llm.llm_enums import OpenAIEnums
from openai import OpenAI
import httpx
import logging
from typing import List, Union




class OpenAIProvider(LLMInterface):
    
    def __init__(self, api_key: str, base_url: str=None,
                default_input_max_char: int=1000,
                default_generation_max_output_tokens: int=1000,
                default_temp: float=0.1):
        
        self.api_key = api_key
        self.base_url = base_url
        
        self.default_temp = default_temp
        self.defalt_input_max_char = default_input_max_char 
        self.default_generation_max_output_tokens = default_generation_max_output_tokens 
        
        # We could change it in RunTime so it's better to assign with None in case we need to use different generation/embedding model and client
        self.generation_model_id = None
        
        self.embedding_model_id = None
        self.embedding_size = None

        http_client = httpx.Client(trust_env=False)

        self.enums = OpenAIEnums
        self.client = OpenAI(
            api_key= self.api_key,
            base_url= self.base_url if self.base_url and len(self.base_url) else None,
            http_client=http_client
        )
        
        self.logger = logging.getLogger(__name__)
        
    def set_generation_model(self, model_id: str):
        self.generation_model_id = model_id
        
    def set_embedding_model(self, model_id: str, embedding_size: int):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size
        
    
    def _process_text(self, text: str):
        return text[:self.defalt_input_max_char].strip()
        
    def generate_text(self, prompt: str, chat_history: list=[], max_output_tokens: int=None, 
                      temp: float = None ):      
        if not self.client:
            self.logger.error("OpenAI client was not set")
            return None
        
        if not self.generation_model_id:
            self.logger.error("Generation model for OpenAI was not set")
            return None
        
        max_output_tokens = max_output_tokens if max_output_tokens  else self.default_generation_max_output_tokens
        temp = temp if temp else self.default_temp
        
        chat_history.append(
            self.construct_prompt(prompt, OpenAIEnums.USER.value)
        )
        
        response = self.client.chat.completions.create(
            model= self.generation_model_id,
            messages = chat_history,
            max_tokens= max_output_tokens,
            temperature=temp
        )
        
        if not response or not response.choices[0].message.content:
            self.logger.error("Error while generating text with OpenAI")
            return None

        return response.choices[0].message.content
    
    
    def embed_text(self, text: Union[str, List[str]], document_type: str = None):
        if not self.client:
            self.logger.error("OpenAI client was not set")
            return None
        
        if isinstance(text, str):
            text = [text]
        
        if not self.embedding_model_id:
            self.logger.error("Embedding model for OpenAI was not set")
            return None
        
        response = self.client.embeddings.create(
            model= self.embedding_model_id,
            input= text
        )
        
        if not response or not response.data or len(response.data) == 0 or not response.data[0].embedding:
            self.logger.error("Error while embedding text with OpenAI")
            return None
        
        return [rec.embedding for rec in response.data]
            
    def construct_prompt(self, prompt: str, role: str):
        return {
            "role" : role,
            "content" : prompt
        }    
    
        
    