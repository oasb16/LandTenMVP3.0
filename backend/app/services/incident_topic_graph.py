"""
Incident Topic Graph - Track multiple parallel issues as a graph structure.
Enables handling of multiple concurrent incidents with automatic topic detection.
"""
import logging
import uuid
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


class IncidentNode:
    """Represents a single incident in the topic graph"""

    def __init__(
        self,
        incident_id: str,
        category: str,
        title: str,
        description: str,
        keywords: Set[str],
    ):
        self.incident_id = incident_id
        self.category = category
        self.title = title
        self.description = description
        self.keywords = keywords
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
        Add a new incident to the graph.

        Args:
            incident_id: Unique incident ID
            category: Category (plumbing, electrical, etc.)
            title: Incident title
            description: Incident description

        Returns:
            Created IncidentNode
        """
        # Extract keywords from title and description
        keywords = self._extract_keywords(title + " " + description)

        # Create node
        node = IncidentNode(
            incident_id=incident_id,
            category=category,
            title=title,
            description=description,
            keywords=keywords,
        )

        # Add to graph
        self.nodes[incident_id] = node
        self.active_incidents.append(incident_id)

        # Index by category
        self.category_index[category].append(incident_id)

        # Index by keywords
        for keyword in keywords:
            self.keyword_index[keyword].append(incident_id)

        logger.info(f"📌 Added incident to graph: {incident_id} ({category})")

        return node

    def detect_topic_shift(
        self,
        new_message: str,
        current_incident_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Detect if new message represents a topic shift (new incident).

        Args:
            new_message: User's new message
            current_incident_id: Currently active incident (if any)

        Returns:
            dict with is_shift (bool), similarity_score (float), reason (str)
        """
        if not current_incident_id or current_incident_id not in self.nodes:
            return {
                "is_shift": True,
                "similarity_score": 0.0,
                "reason": "No active incident",
            }

        current_node = self.nodes[current_incident_id]

        # Extract keywords from new message
        new_keywords = self._extract_keywords(new_message)

        # Calculate keyword overlap
        overlap = current_node.keywords.intersection(new_keywords)
        similarity = len(overlap) / max(len(current_node.keywords), len(new_keywords), 1)

        # Detect category shift
        new_category = self._detect_category(new_message)
        category_match = (new_category == current_node.category) if new_category else True

        # Decision logic
        if similarity > 0.5 and category_match:
            return {
                "is_shift": False,
                "similarity_score": similarity,
                "reason": "High similarity to current incident",
            }
        elif similarity > 0.3:
            return {
                "is_shift": False,
                "similarity_score": similarity,
                "reason": "Moderate similarity, treating as related",
            }
        elif not category_match:
            return {
                "is_shift": True,
                "similarity_score": similarity,
                "reason": f"Category shift: {current_node.category} → {new_category}",
            }
        else:
            return {
                "is_shift": True,
                "similarity_score": similarity,
                "reason": "Low similarity, likely new issue",
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

    def save(self):
        """
        PHASE OMEGA OBJECTIVE #3: TOPIC GRAPH PERSISTENCE
        Save graph to persistent storage
        """
        try:
            # In production, this would save to DynamoDB or Redis
            # For now, we keep it in memory with logging
            logger.info(f"💾 Saving incident graph for user {self.user_id} ({len(self.nodes)} nodes, {len(self.edges)} edges)")
            # TODO: Implement actual persistence to DynamoDB
        except Exception as e:
            logger.error(f"Error saving incident graph: {e}", exc_info=True)

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
        """Load graph from dict"""
        graph = cls(data["user_id"])

        # Reconstruct nodes
        for incident_id, node_data in data["nodes"].items():
            node = IncidentNode(
                incident_id=node_data["incident_id"],
                category=node_data["category"],
                title=node_data["title"],
                description=node_data["description"],
                keywords=set(node_data["keywords"]),
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


# In-memory storage (should be persisted to DB in production)
_incident_graphs: Dict[str, IncidentTopicGraph] = {}


def get_incident_graph(user_id: str) -> IncidentTopicGraph:
    """Get or create incident graph for user"""
    if user_id not in _incident_graphs:
        _incident_graphs[user_id] = IncidentTopicGraph(user_id)
    return _incident_graphs[user_id]
