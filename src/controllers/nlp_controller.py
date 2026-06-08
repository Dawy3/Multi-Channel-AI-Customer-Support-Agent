from .base_controller import BaseController
from models.db_schemes import Project, DataChunk, RetrievedDocument
from stores.llm.llm_enums import DocumentTypeEnum
from typing import List
import json
import logging

logger = logging.getLogger('uvicorn.error')

class NLPController(BaseController):

    def __init__(self, vectordb_client, generation_client, embedding_client, template_parser):
        super().__init__()

        self.embedding_client = embedding_client
        self.vectordb_client = vectordb_client
        self.generation_client = generation_client
        self.template_parser = template_parser
        
    
    def create_collection_name(self, project_id: str):
        size = getattr(self.vectordb_client, "default_vector_size", None) or getattr(self.embedding_client, "embedding_size", None)
        return f"collection_{size}_{project_id}".strip()
    
    async def reset_vector_db_collection(self, project: Project):
        collection_name = self.create_collection_name(project_id= project.project_id)
        return await self.vectordb_client.delete_collection(collection_name)
    
    async def get_vector_db_collection_info(self, project: Project):
        collection_name = self.create_collection_name(project_id= project.project_id)
        collection_info =  await self.vectordb_client.get_collection_info(collection_name)
        
        return json.loads(  # Turn it to json
            json.dumps(collection_info, default= lambda x: x.__dict__)  # Turn Collection info to string -> convert  the objects into dict type
        )
    
    async def index_into_vector_db(self, project: Project, chunks: List[DataChunk],
                             chunks_ids: List[int], do_reset: bool=False):
        # Step1: get collection name
        collection_name = self.create_collection_name(project_id=project.project_id)
        
        # Step2: Mange Items
        # Skip empty/whitespace chunks: OpenAI embeddings rejects empty strings.
        # Keep texts, metadata and ids aligned by filtering them together.
        valid_items = [
            (c.chunk_text, c.chunk_metadata, chunk_id)
            for c, chunk_id in zip(chunks, chunks_ids)
            if c.chunk_text and c.chunk_text.strip()
        ]

        if not valid_items:
            logger.warning("No non-empty chunks to index, skipping")
            return True

        texts, metadata, chunks_ids = map(list, zip(*valid_items))

        vectors = self.embedding_client.embed_text(text=texts, document_type=DocumentTypeEnum.DOCUMENT.value)
        
        # Step3: Create collection if not exists
        _ = await self.vectordb_client.create_collection(
            collection_name= collection_name,
            do_reset=do_reset,
            embedding_size = self.embedding_client.embedding_size,
        )
            
        # Step4: insert into VectorDB
        _ = await self.vectordb_client.insert_many(
            collection_name = collection_name,
            texts= texts,
            vectors= vectors,
            metadata=metadata,
            record_ids = chunks_ids
        )
        
        return True
    
    async def search_vector_db_collection(self, project: Project, text: str, limit: int=10):
        
        # step1 : get collection name
        query_vector = None
        collection_name = self.create_collection_name(project_id=project.project_id)
        
        # step2 : get text embedding vector
        vectors = self.embedding_client.embed_text(text, DocumentTypeEnum.QUERY.value)
        
        if not vectors or len(vectors) == 0:
            return False
        
        if isinstance(vectors, list) and len(vectors) > 0:
            query_vector = vectors[0]
            
        if not query_vector:
            return False
            
        
        # step3 : do semantic search
        results = await self.vectordb_client.search_by_vector(
            collection_name=collection_name,
            vector= query_vector,
            limit=limit
        )
        
        if not results:
            return False

        return results

    def _reciprocal_rank_fusion(self, result_lists: List[List[RetrievedDocument]],
                                limit: int, k: int = 60) -> List[RetrievedDocument]:
        """Combine several ranked result lists into one using Reciprocal Rank Fusion.

        RRF score for a document = sum over each list it appears in of 1 / (k + rank),
        where rank is 1-based. k=60 is the standard constant; it dampens the
        influence of any single high rank so the lists blend smoothly. Documents
        are matched across lists by chunk_id (falling back to text).
        """
        fused_scores = {}
        docs_by_key = {}

        for results in result_lists:
            if not results:
                continue
            for rank, doc in enumerate(results, start=1):
                key = doc.chunk_id if doc.chunk_id is not None else doc.text
                fused_scores[key] = fused_scores.get(key, 0.0) + 1.0 / (k + rank)
                if key not in docs_by_key:
                    docs_by_key[key] = doc

        ranked_keys = sorted(fused_scores, key=fused_scores.get, reverse=True)

        return [
            RetrievedDocument(
                text= docs_by_key[key].text,
                score= fused_scores[key],
                chunk_id= docs_by_key[key].chunk_id,
            )
            for key in ranked_keys[:limit]
        ]

    async def hybrid_search_collection(self, project: Project, text: str, limit: int = 10):
        """Hybrid retrieval: semantic (vector) + lexical (full-text), fused with RRF."""

        collection_name = self.create_collection_name(project_id=project.project_id)

        # Semantic half: embed the query, then vector search
        query_vector = None
        vectors = self.embedding_client.embed_text(text, DocumentTypeEnum.QUERY.value)
        if isinstance(vectors, list) and len(vectors) > 0:
            query_vector = vectors[0]

        semantic_results = []
        if query_vector:
            semantic_results = await self.vectordb_client.search_by_vector(
                collection_name=collection_name,
                vector=query_vector,
                limit=limit,
            ) or []

        # Lexical half: full-text search over the same collection
        lexical_results = await self.vectordb_client.search_by_text(
            collection_name=collection_name,
            text=text,
            limit=limit,
        ) or []

        # Fuse both rankings
        fused = self._reciprocal_rank_fusion(
            result_lists=[semantic_results, lexical_results],
            limit=limit,
        )

        if not fused:
            return False

        return fused

    async def answer_rag_question(self, project: Project, query: str, limit: int=10,
                                  chat_history: list=None):

        answer, full_prompt = None, None

        # The conversation so far = ONLY prior user/assistant turns.
        # (No system prompt, no documents — those are rebuilt every call.)
        chat_history = list(chat_history) if chat_history else []

        # Step1: Retrieve related documents (hybrid: semantic + lexical, RRF-fused)
        retrieved_documents = await self.hybrid_search_collection(
            project=project,
            text= query,
            limit=limit,
        )
        
        if not retrieved_documents or len(retrieved_documents) == 0:
            return answer, full_prompt, chat_history
        
        # Step2: Construct LLM prompt
        system_prompt = self.template_parser.get("rag", "system_prompt")
        
        document_prompts = "\n".join([
            self.template_parser.get("rag", "document_prompt", {
                "doc_num" : i + 1,
                "chunk_text": self.generation_client._process_text(doc.text),
            })
            for i, doc in enumerate(retrieved_documents)
        ])
        
        footer_prompt = self.template_parser.get("rag", "footer_prompt", {"query" : query})

        chat_history.append(
            self.generation_client.construct_prompt(
                role = self.generation_client.enums.USER.value,
                prompt= query,
            )
        )
        
        messages = [
            self.generation_client.construct_prompt(
                role = self.generation_client.enums.SYSTEM.value,
                prompt= system_prompt,
            )
        ] + chat_history[-self.app_settings.CHAT_HISTORY_LIMIT:]
        
        full_prompt = "\n\n".join([document_prompts, footer_prompt])
        
        answer = self.generation_client.generate_text(
            prompt = full_prompt,
            chat_history= messages,
        )

        if not answer:
            return answer, full_prompt, chat_history

        # Step4: store ONLY the clean turn — raw question + raw answer — then cap.
        chat_history.append(
            self.generation_client.construct_prompt(
                role = self.generation_client.enums.ASSISTANT.value,
                prompt= answer,
            )
        )

        return answer, full_prompt, chat_history[-self.app_settings.CHAT_HISTORY_LIMIT:]