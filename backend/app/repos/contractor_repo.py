from typing import Dict, Any, List

from boto3.dynamodb.conditions import Attr

from app.deps.dynamo import get_dynamo_resource, table_name


class ContractorRepo:
    def __init__(self):
        self.table = get_dynamo_resource().Table(table_name("contractor_profiles"))

    def upsert_profile(self, profile: Dict[str, Any]) -> None:
        self.table.put_item(Item=profile)

    def get_profile(self, contractor_id: str) -> Dict[str, Any]:
        resp = self.table.get_item(Key={"contractor_id": contractor_id})
        return resp.get("Item", {})

    def list_by_skill(self, skill: str) -> List[Dict[str, Any]]:
        resp = self.table.scan(
            FilterExpression=Attr("skills").contains(skill)
        )
        return resp.get("Items", [])

    def list_all(self) -> List[Dict[str, Any]]:
        resp = self.table.scan()
        return resp.get("Items", [])
