from typing import Dict, Any, List
from app.deps.dynamo import get_dynamo_resource, table_name


class JobRepo:
    def __init__(self):
        self.table = get_dynamo_resource().Table(table_name("jobs"))

    def create_job(self, job: Dict[str, Any]) -> None:
        self.table.put_item(Item=job)

    def list_jobs(self, user_id: str) -> List[Dict[str, Any]]:
        resp = self.table.query(
            KeyConditionExpression="#uid = :uid",
            ExpressionAttributeNames={"#uid": "user_id"},
            ExpressionAttributeValues={":uid": user_id},
            ScanIndexForward=False,
        )
        return resp.get("Items", [])

