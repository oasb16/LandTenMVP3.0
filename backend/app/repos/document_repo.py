from typing import Dict, Any

from app.deps.dynamo import get_dynamo_resource, table_name


class DocumentRepo:
    def __init__(self):
        self.table = get_dynamo_resource().Table(table_name("documents"))

    def put(self, document: Dict[str, Any]) -> None:
        self.table.put_item(Item=document)

    def get(self, document_id: str) -> Dict[str, Any]:
        resp = self.table.get_item(Key={"document_id": document_id})
        return resp.get("Item", {})
