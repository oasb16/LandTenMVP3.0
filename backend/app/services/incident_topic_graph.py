"""
Incident Topic Graph - Track multiple parallel issues as a graph structure.
Enables handling of multiple concurrent incidents with automatic topic detection.

PHASE OMEGA: True semantic similarity using embeddings, not keyword matching.
"""
import logging
import uuid
import json
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from collections import defaultdict
from decimal import Decimal

logger = logging.getLogger(__name__)

# Try to import embeddings service (graceful degradation)
try:
    from .embeddings_service import get_embeddings_service
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    logger.warning("Embeddings service not available - falling back to keyword matching")


class IncidentNode:
    """Represents a single incident in the topic graph with semantic embedding"""

    def __init__(
        self,
        incident_id: str,
        category: str,
        title: str,
        description: str,
        keywords: Set[str],
        embedding: Optional[List[float]] = None,
    ):
        self.incident_id = incident_id
        self.category = category
        self.title = title
        self.description = description
        self.keywords = keywords
        self.embedding = embedding  # PHASE OMEGA: Semantic vector
        self.created_at = datetime.utcnow().isoformat()
        self.status = "active"
        self.child_incidents: List[str] = []  # Related sub-issues
        self.metadata: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "keywords": list(self.keywords),
            "embedding": self.embedding,  # Include embedding in serialization
            "created_at": self.created_at,
            "status": self.status,
            "child_incidents": self.child_incidents,
            "metadata": self.metadata,
        }


class IncidentTopicGraph:
    """
    Graph structure for tracking multiple parallel incidents.

    Features:
    - Detect topic shifts (new vs related issues)
    - Track incident relationships
    - Enable parallel incident handling
    - Automatic context switching
    - Topic similarity detection
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.nodes: Dict[str, IncidentNode] = {}  # incident_id -> IncidentNode
        self.active_incidents: List[str] = []  # List of active incident IDs
        self.category_index: Dict[str, List[str]] = defaultdict(list)  # category -> incident_ids
        self.keyword_index: Dict[str, List[str]] = defaultdict(list)  # keyword -> incident_ids
        self.edges: List[Dict[str, Any]] = []  # List of edges (relationships)

    def add_incident(
        self,
        incident_id: str,
        category: str,
        title: str,
        description: str,
    ) -> IncidentNode:
        """
        Add a new incident to the graph with semantic embedding.

        Args:
            incident_id: Unique incident ID
            category: Category (plumbing, electrical, etc.)
            title: Incident title
            description: Incident description

        Returns:
            Created IncidentNode
        """
        # Extract keywords from title and description (still useful for fallback)
        keywords = self._extract_keywords(title + " " + description)

        # PHASE OMEGA: Generate semantic embedding
        embedding = None
        if EMBEDDINGS_AVAILABLE:
            try:
                embeddings_service = get_embeddings_service()
                # Combine title and description for rich semantic representation
                text_for_embedding = f"{title}. {description}"
                embedding = embeddings_service.get_embedding(text_for_embedding)

                if embedding:
                    logger.debug(f"✅ Generated embedding for incident {incident_id}")
                else:
                    logger.warning(f"⚠️ Failed to generate embedding for incident {incident_id}")
            except Exception as e:
                logger.error(f"Error generating embedding: {e}", exc_info=True)

        # Create node
        node = IncidentNode(
            incident_id=incident_id,
            category=category,
            title=title,
            description=description,
            keywords=keywords,
            embedding=embedding,
        )

        # Add to graph
        self.nodes[incident_id] = node
        self.active_incidents.append(incident_id)

        # Index by category
        self.category_index[category].append(incident_id)

        # Index by keywords
        for keyword in keywords:
            self.keyword_index[keyword].append(incident_id)

        logger.info(f"📌 Added incident to graph: {incident_id} ({category}) [embedding: {'✅' if embedding else '❌'}]")

        return node

    def detect_topic_shift(
        self,
        new_message: str,
        current_incident_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Detect if new message represents a topic shift (new incident).

        PHASE OMEGA: Uses semantic similarity with embeddings, not keyword matching.

        Args:
            new_message: User's new message
            current_incident_id: Currently active incident (if any)

        Returns:
            dict with is_shift (bool), similarity_score (float), reason (str), method (str)
        """
        if not current_incident_id or current_incident_id not in self.nodes:
            return {
                "is_shift": True,
                "similarity_score": 0.0,
                "reason": "No active incident",
                "method": "no_context",
            }

        current_node = self.nodes[current_incident_id]

        # PHASE OMEGA: Try semantic similarity first (embeddings)
        # Skip embeddings for very short messages to reduce API calls
        if EMBEDDINGS_AVAILABLE and current_node.embedding is not None and len(new_message.strip()) > 10:
            try:
                embeddings_service = get_embeddings_service()
                new_message_embedding = embeddings_service.get_embedding(new_message)

                if new_message_embedding:
                    # Calculate cosine similarity between embeddings
                    similarity = embeddings_service.cosine_similarity(
                        current_node.embedding,
                        new_message_embedding
                    )

                    # Detect category shift
                    new_category = self._detect_category(new_message)
                    category_match = (new_category == current_node.category) if new_category else True

                    # Semantic similarity thresholds (more accurate than keywords)
                    if similarity > 0.75 and category_match:
                        return {
                            "is_shift": False,
                            "similarity_score": similarity,
                            "reason": f"High semantic similarity ({similarity:.2f}) to current incident",
                            "method": "semantic_embeddings",
                        }
                    elif similarity > 0.60:
                        return {
                            "is_shift": False,
                            "similarity_score": similarity,
                            "reason": f"Moderate semantic similarity ({similarity:.2f}), treating as related",
                            "method": "semantic_embeddings",
                        }
                    elif not category_match:
                        return {
                            "is_shift": True,
                            "similarity_score": similarity,
                            "reason": f"Category shift: {current_node.category} → {new_category} (similarity: {similarity:.2f})",
                            "method": "semantic_embeddings",
                        }
                    else:
                        return {
                            "is_shift": True,
                            "similarity_score": similarity,
                            "reason": f"Low semantic similarity ({similarity:.2f}), likely new issue",
                            "method": "semantic_embeddings",
                        }
            except Exception as e:
                logger.error(f"Error in semantic similarity calculation: {e}", exc_info=True)
                # Fall through to keyword matching

        # FALLBACK: Keyword-based similarity (when embeddings unavailable)
        logger.warning("Using fallback keyword matching for topic shift detection")

        # Extract keywords from new message
        new_keywords = self._extract_keywords(new_message)

        # Calculate keyword overlap
        overlap = current_node.keywords.intersection(new_keywords)
        similarity = len(overlap) / max(len(current_node.keywords), len(new_keywords), 1)

        # Detect category shift
        new_category = self._detect_category(new_message)
        category_match = (new_category == current_node.category) if new_category else True

        # Decision logic (keyword-based)
        if similarity > 0.5 and category_match:
            return {
                "is_shift": False,
                "similarity_score": similarity,
                "reason": f"High keyword overlap ({similarity:.2f}) to current incident",
                "method": "keyword_fallback",
            }
        elif similarity > 0.3:
            return {
                "is_shift": False,
                "similarity_score": similarity,
                "reason": f"Moderate keyword overlap ({similarity:.2f}), treating as related",
                "method": "keyword_fallback",
            }
        elif not category_match:
            return {
                "is_shift": True,
                "similarity_score": similarity,
                "reason": f"Category shift: {current_node.category} → {new_category}",
                "method": "keyword_fallback",
            }
        else:
            return {
                "is_shift": True,
                "similarity_score": similarity,
                "reason": f"Low keyword overlap ({similarity:.2f}), likely new issue",
                "method": "keyword_fallback",
            }

    def get_active_incidents(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all active incidents, optionally filtered by status"""
        incidents = []

        for incident_id in self.active_incidents:
            node = self.nodes.get(incident_id)
            if node:
                if status_filter is None or node.status == status_filter:
                    incidents.append(node.to_dict())

        return incidents

    def find_similar_incidents(
        self,
        query_text: str,
        top_k: int = 5,
        min_similarity: float = 0.6,
        category_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        PHASE OMEGA: Vector search - find incidents most similar to query text.

        Args:
            query_text: Text to search for
            top_k: Number of top results to return
            min_similarity: Minimum similarity threshold (0.0-1.0)
            category_filter: Optional category to filter by

        Returns:
            List of dicts with incident data and similarity scores
        """
        if not EMBEDDINGS_AVAILABLE:
            logger.warning("Embeddings not available for vector search")
            return []

        try:
            embeddings_service = get_embeddings_service()
            query_embedding = embeddings_service.get_embedding(query_text)

            if not query_embedding:
                logger.error("Failed to generate query embedding")
                return []

            # Calculate similarity to all incidents
            results = []
            for incident_id, node in self.nodes.items():
                # Skip if no embedding
                if node.embedding is None:
                    continue

                # Apply category filter
                if category_filter and node.category != category_filter:
                    continue

                # Calculate similarity
                similarity = embeddings_service.cosine_similarity(
                    query_embedding,
                    node.embedding
                )

                if similarity >= min_similarity:
                    results.append({
                        "incident_id": incident_id,
                        "title": node.title,
                        "category": node.category,
                        "description": node.description,
                        "similarity": similarity,
                        "status": node.status,
                        "created_at": node.created_at,
                    })

            # Sort by similarity descending
            results.sort(key=lambda x: x["similarity"], reverse=True)

            # Return top K
            return results[:top_k]

        except Exception as e:
            logger.error(f"Error in vector search: {e}", exc_info=True)
            return []

    def update_incident_status(self, incident_id: str, status: str):
        """Update incident status"""
        if incident_id in self.nodes:
            self.nodes[incident_id].status = status

            # Remove from active if completed
            if status == "completed" and incident_id in self.active_incidents:
                self.active_incidents.remove(incident_id)

            logger.info(f"📝 Updated incident status: {incident_id} → {status}")

    def link_incidents(self, parent_id: str, child_id: str):
        """Create parent-child relationship between incidents"""
        if parent_id in self.nodes and child_id in self.nodes:
            self.nodes[parent_id].child_incidents.append(child_id)
            logger.info(f"🔗 Linked incidents: {parent_id} → {child_id}")

    def add_node(self, node_type: str, node_id: str, metadata: Dict[str, Any]):
        """
        PHASE OMEGA: Add a generic node to the graph (incident, work_order, etc.)

        Args:
            node_type: Type of node (incident, work_order, diagnosis, etc.)
            node_id: Unique ID for the node
            metadata: Additional metadata for the node
        """
        # For work orders and other non-incident nodes, store as metadata
        if node_type == "work_order":
            # Create a simple node structure for work orders
            if node_id not in self.nodes:
                # Create minimal incident-like node for work orders
                work_order_node = IncidentNode(
                    incident_id=node_id,
                    category="work_order",
                    title=metadata.get("title", f"Work Order {node_id}"),
                    description=f"Work order for incident {metadata.get('incident_id', 'unknown')}",
                    keywords=set(),
                )
                work_order_node.metadata = metadata
                self.nodes[node_id] = work_order_node
                logger.info(f"📌 Added work order node: {node_id}")

    def add_edge(self, from_id: str, to_id: str, edge_type: str):
        """
        PHASE OMEGA: Add an edge (relationship) between two nodes

        Args:
            from_id: Source node ID
            to_id: Target node ID
            edge_type: Type of relationship (work_order_created, related_to, etc.)
        """
        edge = {
            "from": from_id,
            "to": to_id,
            "type": edge_type,
            "created_at": datetime.utcnow().isoformat(),
        }
        self.edges.append(edge)
        logger.info(f"🔗 Added edge: {from_id} → {to_id} ({edge_type})")

    def add_relation(self, from_id: str, to_id: str, relation_type: str):
        """Alias for add_edge() for compatibility"""
        self.add_edge(from_id, to_id, relation_type)

    def add_work_order(self, incident_id: str, job_id: str, title: str):
        """
        PHASE OMEGA: Convenience method to add work order and link to incident

        Args:
            incident_id: Parent incident ID
            job_id: Work order job ID
            title: Work order title
        """
        metadata = {
            "incident_id": incident_id,
            "title": title,
            "type": "work_order",
        }
        self.add_node("work_order", job_id, metadata)
        self.add_edge(incident_id, job_id, "work_order_created")
        logger.info(f"📋 Added work order {job_id} for incident {incident_id}")

    def save(self, retry_count: int = 0, max_retries: int = 3):
        """
        PHASE OMEGA OBJECTIVE #3: TOPIC GRAPH PERSISTENCE
        Save graph to persistent storage (DynamoDB) with retry logic.

        Args:
            retry_count: Current retry attempt (internal)
            max_retries: Maximum number of retries
        """
        # 🚨 CRITICAL FIX: Don't save empty graphs (wastes DynamoDB writes)
        if len(self.nodes) == 0:
            logger.debug(f"⏭️ Skipping save of empty incident graph for user {self.user_id}")
            return

        try:
            from ..services.dynamo_service import get_dynamodb_resource

            # Get DynamoDB resource and table
            dynamodb = get_dynamodb_resource()
            table = dynamodb.Table("landten_incidents")  # Use existing table

            # Serialize graph to dict
            graph_data = self.to_dict()

            # Convert to DynamoDB-compatible format (replace floats with Decimal)
            graph_data_serialized = self._convert_to_dynamo_format(graph_data)

            print("===== user_id: ========", self.user_id)

            # Save to DynamoDB with PK/SK pattern
            # SCHEMA FIX: landten_incidents has PK=user_id, SK=incident_id
            item = {
                "user_id": self.user_id,  # PK: user_id
                "incident_id": f"GRAPH#{self.user_id}",  # SK: incident_id with GRAPH# prefix
                "tenant_id": self.user_id,  # Keep for compatibility
                "graph_data": graph_data_serialized,  # Store dict directly, no json.dumps
                "node_count": len(self.nodes),
                "edge_count": len(self.edges),
                "updated_at": datetime.utcnow().isoformat(),
                "created_at": datetime.utcnow().isoformat(),
                "status": "active",
                "title": "Topic Graph Metadata",
                "description": "Incident topic graph storage",
                "category": "system",
                "severity": "low",
                "urgency": "routine",
            }

            table.put_item(Item=item)

            logger.info(f"💾 Saved incident graph for user {self.user_id} ({len(self.nodes)} nodes, {len(self.edges)} edges)")

        except Exception as e:
            if retry_count < max_retries:
                import time
                wait_time = 2 ** retry_count  # Exponential backoff: 1s, 2s, 4s
                logger.warning(f"⚠️ Failed to save graph (attempt {retry_count + 1}/{max_retries}), retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
                self.save(retry_count=retry_count + 1, max_retries=max_retries)
            else:
                logger.error(f"❌ Failed to save incident graph after {max_retries} retries: {e}", exc_info=True)
                # Don't raise - gracefully degrade to in-memory only

    def _convert_to_dynamo_format(self, data: Any) -> Any:
        """
        Recursively convert data to DynamoDB-compatible format.
        Replaces float with Decimal, handles sets, etc.
        """
        if isinstance(data, dict):
            return {k: self._convert_to_dynamo_format(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._convert_to_dynamo_format(item) for item in data]
        elif isinstance(data, set):
            return list(data)  # Convert sets to lists
        elif isinstance(data, float):
            return Decimal(str(data))
        else:
            return data

    @staticmethod
    def _convert_from_dynamo_format(data: Any) -> Any:
        """
        Recursively convert DynamoDB format back to Python native types.
        Converts Decimal to float, handles nested structures.
        """
        if isinstance(data, dict):
            return {k: IncidentTopicGraph._convert_from_dynamo_format(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [IncidentTopicGraph._convert_from_dynamo_format(item) for item in data]
        elif isinstance(data, Decimal):
            return float(data)
        else:
            return data

    @classmethod
    def load_from_dynamodb(cls, user_id: str) -> Optional["IncidentTopicGraph"]:
        """
        Load graph from DynamoDB for a user.

        Args:
            user_id: User ID to load graph for

        Returns:
            IncidentTopicGraph instance or None if not found
        """
        try:
            from ..services.dynamo_service import get_dynamodb_resource

            dynamodb = get_dynamodb_resource()
            table = dynamodb.Table("landten_incidents")

            # Query DynamoDB using composite primary key (PK + SK)
            # SCHEMA FIX: landten_incidents has PK=user_id, SK=incident_id
            response = table.get_item(
                Key={
                    "user_id": user_id,                  # PK
                    "incident_id": f"GRAPH#{user_id}",  # SK
                }
            )

            if "Item" not in response:
                logger.debug(f"No saved incident graph found for user {user_id}")
                return None

            item = response["Item"]
            graph_data_raw = item.get("graph_data")

            if not graph_data_raw:
                return None

            # Handle both old format (JSON string) and new format (dict)
            if isinstance(graph_data_raw, str):
                # Old format: JSON-encoded string
                graph_data = json.loads(graph_data_raw)
            else:
                # New format: dict with Decimals, convert Decimals back to floats
                graph_data = cls._convert_from_dynamo_format(graph_data_raw)

            # Reconstruct graph from dict
            graph = cls.from_dict(graph_data)

            logger.info(f"📂 Loaded incident graph for user {user_id} ({len(graph.nodes)} nodes, {len(graph.edges)} edges)")

            return graph

        except Exception as e:
            logger.error(f"Error loading incident graph from DynamoDB: {e}", exc_info=True)
            return None

    def _extract_keywords(self, text: str) -> Set[str]:
        """Extract meaningful keywords from text"""
        # Simple keyword extraction (can be enhanced with NLP)
        import re

        # Convert to lowercase
        text = text.lower()

        # Remove punctuation
        text = re.sub(r'[^\w\s]', ' ', text)

        # Split into words
        words = text.split()

        # Filter stopwords and short words
        stopwords = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "is", "are", "was", "were", "been", "be",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "must", "can", "my", "your", "its", "it",
        }

        keywords = {
            word for word in words
            if len(word) > 3 and word not in stopwords
        }

        return keywords

    def _detect_category(self, text: str) -> Optional[str]:
        """Simple category detection from text"""
        text_lower = text.lower()

        category_keywords = {
            "plumbing": ["leak", "pipe", "sink", "toilet", "faucet", "drain", "water", "clog"],
            "electrical": ["outlet", "light", "switch", "power", "breaker", "spark", "wire"],
            "hvac": ["heat", "ac", "air", "thermostat", "furnace", "cooling", "temperature"],
            "appliance": ["fridge", "refrigerator", "washer", "dryer", "dishwasher", "oven", "stove"],
            "structural": ["wall", "ceiling", "floor", "door", "window", "crack", "hole"],
        }

        for category, keywords in category_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return category

        return None

    def to_dict(self) -> Dict[str, Any]:
        """Export graph to dict for serialization"""
        return {
            "user_id": self.user_id,
            "nodes": {
                incident_id: node.to_dict()
                for incident_id, node in self.nodes.items()
            },
            "active_incidents": self.active_incidents,
            "edges": self.edges,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IncidentTopicGraph":
        """Load graph from dict with embeddings support"""
        graph = cls(data["user_id"])

        # Reconstruct nodes
        for incident_id, node_data in data["nodes"].items():
            node = IncidentNode(
                incident_id=node_data["incident_id"],
                category=node_data["category"],
                title=node_data["title"],
                description=node_data["description"],
                keywords=set(node_data["keywords"]),
                embedding=node_data.get("embedding"),  # PHASE OMEGA: Restore embeddings
            )
            node.status = node_data["status"]
            node.created_at = node_data["created_at"]
            node.child_incidents = node_data["child_incidents"]
            node.metadata = node_data["metadata"]

            graph.nodes[incident_id] = node

            # Rebuild indexes
            graph.category_index[node.category].append(incident_id)
            for keyword in node.keywords:
                graph.keyword_index[keyword].append(incident_id)

        graph.active_incidents = data["active_incidents"]
        graph.edges = data.get("edges", [])

        return graph


# In-memory cache for performance (backed by DynamoDB)
_incident_graphs: Dict[str, IncidentTopicGraph] = {}


def get_incident_graph(user_id: str) -> IncidentTopicGraph:
    """
    Get or create incident graph for user.
    First checks in-memory cache, then loads from DynamoDB, or creates new.
    """
    # Check in-memory cache first
    if user_id in _incident_graphs:
        return _incident_graphs[user_id]

    # Try to load from DynamoDB
    graph = IncidentTopicGraph.load_from_dynamodb(user_id)

    if graph is None:
        # Create new graph if not found
        logger.debug(f"Creating new incident graph for user {user_id}")
        graph = IncidentTopicGraph(user_id)

    # Cache in memory
    _incident_graphs[user_id] = graph

    return graph
