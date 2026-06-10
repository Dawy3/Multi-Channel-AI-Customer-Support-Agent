from qdrant_client import QdrantClient, models
from ..vectorDB_interface import VectorDBInterface
from ..vectorDB_enums import DistanceMethodEnums
from models.db_schemes import RetrievedDocument
import logging
from typing import List

class QdrantDB(VectorDBInterface):

    def __init__(self, db_client, default_vector_size: int = 786,
                distance_method: str= None, index_threshold: int = 100,
                url: str = None, api_key: str = None):

        self.client = None
        self.db_client = db_client
        self.url = url
        self.api_key = api_key
        self.distance_method = None
        self.default_vector_size = default_vector_size
        # Payload key under which chunk text is stored (see insert_many)
        self.text_payload_key = "texts"


        if distance_method == DistanceMethodEnums.COSINE.value:
            self.distance_method = models.Distance.COSINE
        elif distance_method == DistanceMethodEnums.DOT.value:
            self.distance_method = models.Distance.DOT
            
        
        self.logger = logging.getLogger("uvicorn")
        
    async def connect(self):
        # Qdrant Cloud (or any remote server) when a URL is provided,
        # otherwise fall back to the local embedded store at db_client path.
        if self.url:
            self.client = QdrantClient(url=self.url, api_key=self.api_key)
        else:
            self.client = QdrantClient(path=self.db_client)
        
    async def disconnect(self):
        self.client = None
        
    async def is_collection_existed(self, collection_name: str) -> bool:
        return self.client.collection_exists(collection_name=collection_name)
        
    async def list_all_collection(self) -> List:
        return self.client.get_collections()

    async def get_collection_info(self, collection_name: str) -> dict:
        return self.client.get_collection(collection_name=collection_name)
    
    async def delete_collection(self, collection_name: str): 
        if self.is_collection_existed(collection_name):
            self.logger.info(f"Deleting collection: {collection_name}")
            return self.client.delete_collection(collection_name=collection_name)
            
    async def create_collection(self, collection_name: str,
                          embedding_size: int,
                          do_reset: bool = False):
        if do_reset:
            _ = self.delete_collection(collection_name)
            
        if not self.is_collection_existed(collection_name):
            self.logger.info(f"Creating new Qdrant Collection: {collection_name}")
            _ = self.client.create_collection(
                collection_name=collection_name,
                vectors_config= models.VectorParams(size=embedding_size, distance= self.distance_method)
            )

            # Payload text index enables lexical (full-text) MatchText search.
            # MULTILINGUAL tokenizer handles ar / en / es uniformly.
            self.client.create_payload_index(
                collection_name=collection_name,
                field_name=self.text_payload_key,
                field_schema=models.TextIndexParams(
                    type=models.TextIndexType.TEXT,
                    tokenizer=models.TokenizerType.MULTILINGUAL,
                    min_token_len=2,
                    lowercase=True,
                ),
            )
            return True
        return False
    
    async def insert_one(self, collection_name: str, text: str, vector: list,
                   metadata: dict=None, record_id: str=None):
        
        if not self.is_collection_existed(collection_name):
            self.logger.error(f"Can not insert new record to non-existed collection {collection_name}")
            return False
        try:
            _ = self.client.upload_records(
                collection_name=collection_name,
                records=[
                    models.Record(
                        id= [record_id],
                        vector=vector,
                        payload={
                            "text": text, "metadata" : metadata,
                            }
                    )
                ]
            )
        except Exception as e:
                self.logger.error(f"Error while inserting batch: {e}")
                return False
            
        return True
    
    async def insert_many(self, collection_name: str, texts: list, vectors: list,
                    metadata: list = None, record_ids: list=None, batch_size: int=50):
        
        if metadata is None:
            metadata = [None] * len(texts)          # for batch_size loop
            
        if record_ids is None:
            record_ids = list(range(0, len(texts)))
            
        for i in range(0, len(texts), batch_size):
            batch_end = i + batch_size
            
            batch_texts = texts[i: batch_end]
            batch_vectors = vectors[i: batch_end]
            batch_metadata = metadata[i: batch_end]
            batch_record_ids = record_ids[i: batch_end]
            
            batch_records = [
                models.Record(
                    id = batch_record_ids[x],
                    vector = batch_vectors[x],
                    payload= {
                        "texts" : batch_texts[x], "metadata": batch_metadata[x]
                    }
                )
                
                for x in range(len(batch_texts))
            ] 
            try:
                _ = self.client.upload_records(
                    collection_name=collection_name,
                    records= batch_records,
                )
            except Exception as e:
                self.logger.error(f"Error while inserting batch: {e}")
                return False
        
        return True
            
    async def search_by_vector(self, collection_name: str, vector: list, limit: int= 5):

        results = self.client.search(
            collection_name=collection_name,
            query_vector=vector,
            limit= limit
        )

        if not results or len(results) == 0:
            return None

        return [
            RetrievedDocument(
                score= result.score,
                text= result.payload[self.text_payload_key],
                chunk_id= result.id,
            )
            for result in results
        ]

    async def search_by_text(self, collection_name: str, text: str, limit: int = 5):

        if not self.is_collection_existed(collection_name):
            self.logger.error(f"Can not search non-existed collection {collection_name}")
            return None

        # MatchText is a filter, not a scorer: it selects matching points but
        # does not rank them by relevance. We keep insertion/scroll order and let
        # RRF use the rank position. (True lexical scoring in Qdrant needs sparse
        # vectors / BM25, which this provider does not set up.)
        records, _ = self.client.scroll(
            collection_name=collection_name,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key=self.text_payload_key,
                        match=models.MatchText(text=text),
                    )
                ]
            ),
            limit=limit,
            with_payload=True,
        )

        if not records or len(records) == 0:
            return None

        # Positional score (descending) so ordering is preserved for fusion.
        return [
            RetrievedDocument(
                score= float(limit - i),
                text= record.payload[self.text_payload_key],
                chunk_id= record.id,
            )
            for i, record in enumerate(records)
        ]