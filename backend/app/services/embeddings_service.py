"""
Embeddings Service - Semantic similarity using OpenAI embeddings.
Provides vector embeddings for text, cosine similarity, and semantic search.

PHASE OMEGA: True semantic understanding, not keyword matching.
"""
import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from openai import OpenAI
import hashlib
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class EmbeddingsService:
    """
    Service for generating and comparing text embeddings using OpenAI.

    Features:
    - Generate embeddings for text
    - Calculate cosine similarity
    - Semantic search across documents
    - Caching for performance
    - Batch processing
    """

    def __init__(self, model: str = "text-embedding-3-small"):
        """
        Initialize embeddings service.

        Args:
            model: OpenAI embedding model to use
                   - text-embedding-3-small: Fast, 1536 dimensions
                   - text-embedding-3-large: More accurate, 3072 dimensions
        """
        self.model = model
        self.client = None
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = timedelta(hours=24)  # Cache for 24 hours

    def _get_client(self) -> OpenAI:
        """Get or create OpenAI client"""
        if self.client is None:
            self.client = OpenAI()  # Uses OPENAI_API_KEY from env
        return self.client

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        return hashlib.md5(text.encode()).hexdigest()

    def get_embedding(self, text: str, use_cache: bool = True) -> Optional[List[float]]:
        """
        Get embedding for text.

        Args:
            text: Text to embed
            use_cache: Whether to use cached embeddings

        Returns:
            Embedding vector (list of floats) or None on error
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return None

        # Check cache
        if use_cache:
            cache_key = self._get_cache_key(text)
            if cache_key in self.cache:
                cached = self.cache[cache_key]
                # Check if cache is still valid
                if datetime.now() - cached["timestamp"] < self.cache_ttl:
                    logger.debug(f"Cache hit for text: {text[:50]}...")
                    return None
                    #return cached["embedding"]
                else:
                    # Cache expired
                    del self.cache[cache_key]

        # Generate embedding
        try:
            client = self._get_client()
            response = client.embeddings.create(
                input=text,
                model=self.model
            )

            embedding = response.data[0].embedding

            # Cache result
            if use_cache:
                cache_key = self._get_cache_key(text)
                self.cache[cache_key] = {
                    #"embedding": embedding,
                    "timestamp": datetime.now(),
                    "text_length": len(text),
                }

            logger.debug(f"Generated embedding for text: {text[:50]}... (dim: {len(embedding)})")
            return embedding

        except Exception as e:
            logger.error(f"Error generating embedding: {e}", exc_info=True)
            return None

    def get_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Get embeddings for multiple texts (batch processing).

        Args:
            texts: List of texts to embed

        Returns:
            List of embeddings (same order as input)
        """
        if not texts:
            return []

        # Filter out empty texts and track indices
        valid_texts = []
        valid_indices = []
        for i, text in enumerate(texts):
            if text and text.strip():
                valid_texts.append(text)
                valid_indices.append(i)

        if not valid_texts:
            return [None] * len(texts)

        try:
            client = self._get_client()
            response = client.embeddings.create(
                input=valid_texts,
                model=self.model
            )

            # Map embeddings back to original indices
            embeddings = [None] * len(texts)
            for i, embedding_obj in enumerate(response.data):
                original_index = valid_indices[i]
                embeddings[original_index] = embedding_obj.embedding

            logger.info(f"Generated {len(valid_texts)} embeddings in batch")
            return embeddings

        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}", exc_info=True)
            return [None] * len(texts)

    def cosine_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Similarity score (0.0 to 1.0, where 1.0 is identical)
        """
        if not embedding1 or not embedding2:
            return 0.0

        if len(embedding1) != len(embedding2):
            logger.warning(f"Embedding dimension mismatch: {len(embedding1)} vs {len(embedding2)}")
            return 0.0

        # Convert to numpy arrays
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        # Calculate cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)

        # Normalize to 0-1 range (cosine similarity is -1 to 1, but embeddings should be 0-1)
        normalized = (similarity + 1) / 2
        return float(normalized)

    def text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate semantic similarity between two texts.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score (0.0 to 1.0)
        """
        embedding1 = self.get_embedding(text1)
        embedding2 = self.get_embedding(text2)

        if embedding1 is None or embedding2 is None:
            logger.warning("Failed to generate embeddings for similarity comparison")
            return 0.0

        return self.cosine_similarity(embedding1, embedding2)

    def find_most_similar(
        self,
        query_text: str,
        candidates: List[Dict[str, Any]],
        text_field: str = "text",
        top_k: int = 5,
        min_similarity: float = 0.5
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Find most similar items from a list of candidates.

        Args:
            query_text: Text to search for
            candidates: List of candidate items (dicts with text field)
            text_field: Field name containing text to compare
            top_k: Number of top results to return
            min_similarity: Minimum similarity threshold

        Returns:
            List of (item, similarity_score) tuples, sorted by similarity descending
        """
        # Get query embedding
        query_embedding = self.get_embedding(query_text)
        if query_embedding is None:
            return []

        # Get embeddings for all candidates
        candidate_texts = [item.get(text_field, "") for item in candidates]
        candidate_embeddings = self.get_embeddings_batch(candidate_texts)

        # Calculate similarities
        similarities = []
        for i, candidate_embedding in enumerate(candidate_embeddings):
            if candidate_embedding is None:
                continue

            similarity = self.cosine_similarity(query_embedding, candidate_embedding)

            if similarity >= min_similarity:
                similarities.append((candidates[i], similarity))

        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Return top K
        return similarities[:top_k]

    def cluster_by_similarity(
        self,
        items: List[Dict[str, Any]],
        text_field: str = "text",
        similarity_threshold: float = 0.7
    ) -> List[List[Dict[str, Any]]]:
        """
        Cluster items by semantic similarity.

        Args:
            items: List of items to cluster
            text_field: Field containing text
            similarity_threshold: Minimum similarity to be in same cluster

        Returns:
            List of clusters (each cluster is a list of items)
        """
        if not items:
            return []

        # Get embeddings for all items
        texts = [item.get(text_field, "") for item in items]
        embeddings = self.get_embeddings_batch(texts)

        # Initialize clusters
        clusters: List[List[int]] = []  # List of lists of indices
        clustered: set[int] = set()  # Track which items are clustered

        # Greedy clustering
        for i in range(len(items)):
            if i in clustered or embeddings[i] is None:
                continue

            # Start new cluster with this item
            cluster = [i]
            clustered.add(i)

            # Find similar items
            for j in range(i + 1, len(items)):
                if j in clustered or embeddings[j] is None:
                    continue

                # Check similarity to cluster representative (first item)
                similarity = self.cosine_similarity(embeddings[i], embeddings[j])

                if similarity >= similarity_threshold:
                    cluster.append(j)
                    clustered.add(j)

            clusters.append(cluster)

        # Convert index clusters to item clusters
        result_clusters = []
        for cluster_indices in clusters:
            cluster_items = [items[i] for i in cluster_indices]
            result_clusters.append(cluster_items)

        logger.info(f"Clustered {len(items)} items into {len(result_clusters)} clusters")
        return result_clusters

    def clear_cache(self):
        """Clear embedding cache"""
        self.cache.clear()
        logger.info("Embedding cache cleared")


# Singleton instance
_embeddings_service: Optional[EmbeddingsService] = None


def get_embeddings_service() -> EmbeddingsService:
    """Get singleton instance of EmbeddingsService"""
    global _embeddings_service
    if _embeddings_service is None:
        _embeddings_service = EmbeddingsService()
    return _embeddings_service
