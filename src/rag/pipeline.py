"""
RAG Pipeline orchestrator.

High-level interface for the complete RAG workflow:
1. Ingest documents
2. Chunk texts
3. Generate embeddings
4. Store in vector database
5. Query/retrieve relevant context
"""

import logging
from pathlib import Path
from typing import List, Union, Optional, Dict, Any

from .ingestion import DocumentIngester, IngestionConfig
from .chunker import TextChunker, ChunkConfig
from .embeddings import EmbeddingGenerator, EmbeddingConfig
from .vectorstore import FAISSVectorStore
from .retriever import RAGRetriever, RAGQuery
from .models import Document, DocumentChunk

logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    End-to-end RAG pipeline with convenient interface.

    Manages the complete workflow from document ingestion to retrieval.
    Automatically coordinates chunker, embedder, and vector store.
    """

    def __init__(self,
                 index_path: Optional[str] = None,
                 org_id: str = "default",
                 config: Optional[Dict[str, Any]] = None):
        """
        Initialize RAG pipeline.

        Args:
            index_path: Path to persist FAISS index (None = in-memory only)
            org_id: Default organization ID for filtering
            config: Optional configuration overrides
        """
        self.org_id = org_id
        self.index_path = index_path

        # Configuration with defaults
        self.config = {
            "chunk_size": 500,
            "chunk_overlap": 50,
            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
            "batch_size": 32,
            "allowed_extensions": [".pdf", ".txt", ".md", ".csv", ".json", ".docx", ".log", ".rst", ".html", ".xml", ".png", ".jpg", ".jpeg", ".webp", ".bmp"],
            ** (config or {})
        }

        # Initialize components
        logger.info("Initializing RAG pipeline...")

        self.embedding_gen = EmbeddingGenerator(EmbeddingConfig(
            model_name=self.config["embedding_model"],
            batch_size=self.config["batch_size"]
        ))

        self.vector_store = FAISSVectorStore(
            self.embedding_gen,
            index_path=index_path
        )

        self.chunker = TextChunker(ChunkConfig(
            chunk_size=self.config["chunk_size"],
            overlap=self.config["chunk_overlap"]
        ))

        self.retriever = RAGRetriever(self.vector_store, self.embedding_gen)

        self.ingester = DocumentIngester(IngestionConfig(
            allowed_extensions=self.config["allowed_extensions"]
        ))

        logger.info(f"Pipeline initialized (dim={self.embedding_gen.dimension})")

    def ingest_and_index(self, sources: List[Union[str, Path]],
                        document_type: Optional[str] = None,
                        start_page: Optional[int] = None,
                        end_page: Optional[int] = None) -> Dict[str, Any]:
        """
        Ingest documents and add them to the vector index with optional page range.

        Args:
            sources: List of file paths or directory paths
            document_type: Override document type (auto-detected if None)
            start_page: Optional 1-indexed start page
            end_page: Optional 1-indexed end page

        Returns:
            Dict with stats: {'documents': N, 'chunks': M, 'errors': K}
        """
        stats = {
            "documents_ingested": 0,
            "chunks_created": 0,
            "errors": 0
        }

        all_documents = []

        # Step 1: Ingest
        for source in sources:
            source_path = Path(source)

            if source_path.is_file():
                doc = self.ingester.ingest_file(
                    source_path,
                    self.org_id,
                    document_type,
                    start_page=start_page,
                    end_page=end_page
                )
                if doc:
                    all_documents.append(doc)
                else:
                    stats["errors"] += 1
            elif source_path.is_dir():
                docs = self.ingester.ingest_directory(source_path, self.org_id, document_type)
                all_documents.extend(docs)
                if not docs:
                    stats["errors"] += 1
            else:
                logger.error(f"Source not found: {source}")
                stats["errors"] += 1

        stats["documents_ingested"] = len(all_documents)

        if not all_documents:
            logger.warning("No documents to process")
            return stats

        # Step 2: Chunk
        chunks_data = self.chunker.chunk_documents(
            [d.model_dump() for d in all_documents],
            text_key="content"
        )
        stats["chunks_created"] = len(chunks_data)

        if not chunks_data:
            logger.warning("No chunks created")
            return stats

        # Step 3: Create DocumentChunk objects
        chunk_objects = []
        for chunk_dict in chunks_data:
            doc_meta = chunk_dict.get("doc_metadata") or {}
            chunk_obj = DocumentChunk(
                id=chunk_dict["chunk_id"],
                document_id=chunk_dict["document_id"],
                org_id=self.org_id,
                chunk_index=chunk_dict["chunk_index"],
                text=chunk_dict["text"],
                metadata={
                    "token_count": chunk_dict["token_count"],
                    "segment_count": chunk_dict["segment_count"],
                    "title": chunk_dict.get("title") or doc_meta.get("file_name", ""),
                    "source": chunk_dict.get("source_path") or doc_meta.get("file_name", ""),
                    **doc_meta
                }
            )
            chunk_objects.append(chunk_obj)

        # Step 4: Generate embeddings
        texts = [c.text for c in chunk_objects]
        logger.info(f"Generating embeddings for {len(texts)} chunks...")
        embeddings = self.embedding_gen.generate(texts)

        # Step 5: Store in vector store
        for chunk_obj, embedding in zip(chunk_objects, embeddings):
            chunk_obj.embedding = embedding

        self.vector_store.add_chunks(chunk_objects)

        # Step 6: Save index if path specified
        if self.index_path:
            self.vector_store.save(self.index_path)

        logger.info(
            f"Ingestion complete: {stats['documents_ingested']} docs, "
            f"{stats['chunks_created']} chunks, {self.vector_store.total_vectors} total vectors"
        )

        return stats

    def query(self,
              query: str,
              top_k: int = 5,
              min_score: float = 0.0,
              filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Query for relevant context.

        Args:
            query: Search query
            top_k: Number of results
            min_score: Minimum similarity threshold
            filters: Metadata filters

        Returns:
            List of result dicts with text, score, metadata
        """
        rag_query = RAGQuery(
            query=query,
            org_id=self.org_id,
            top_k=top_k,
            min_score=min_score,
            filters=filters or {}
        )

        response = self.retriever.retrieve(rag_query)
        return [
            {
                "text": r.chunk.text,
                "score": float(r.similarity_score),
                "rank": r.rank,
                "chunk_id": r.chunk.id,
                "document_id": r.chunk.document_id,
                "metadata": r.chunk.metadata
            }
            for r in response.results
        ]

    def get_stats(self) -> Dict[str, Any]:
        """
        Get pipeline statistics.

        Returns:
            Dict with vector store stats
        """
        return self.vector_store.get_stats()

    def clear(self):
        """Clear all data from the vector store."""
        self.vector_store.clear()
        if self.index_path:
            # Delete persisted files
            faiss_path = f"{self.index_path}.faiss"
            meta_path = f"{self.index_path}.meta"
            for p in [faiss_path, meta_path]:
                if Path(p).exists():
                    Path(p).unlink()
            logger.info("Cleared persisted index files")


def create_pipeline(index_path: Optional[str] = None,
                   org_id: str = "default",
                   **kwargs) -> RAGPipeline:
    """
    Factory function to create RAG pipeline.

    Args:
        index_path: Optional path to persist FAISS index
        org_id: Organization ID for multi-tenancy
        **kwargs: Additional configuration overrides

    Returns:
        Configured RAGPipeline instance

    Example:
        >>> pipeline = create_pipeline(index_path="data/rag_index", org_id="org_123")
        >>> pipeline.ingest_and_index(["docs/metrics.md", "docs/incidents/"])
        >>> results = pipeline.query("Why did revenue drop?", top_k=3)
    """
    config = kwargs if kwargs else None
    return RAGPipeline(index_path=index_path, org_id=org_id, config=config)
