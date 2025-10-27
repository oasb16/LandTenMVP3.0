from typing import Dict, Any, List

from boto3.dynamodb.conditions import Attr

from app.deps.dynamo import get_dynamo_resource, table_name


class JobBidRepo:
    def __init__(self):
        self.table = get_dynamo_resource().Table(table_name("job_bids"))

    def create_bid(self, bid: Dict[str, Any]) -> None:
        self.table.put_item(Item=bid)

    def list_for_job(self, job_id: str) -> List[Dict[str, Any]]:
        resp = self.table.scan(
            FilterExpression=Attr("job_id").eq(job_id)
        )
        return resp.get("Items", [])

    def list_for_contractor(self, contractor_id: str) -> List[Dict[str, Any]]:
        resp = self.table.scan(
            FilterExpression=Attr("contractor_id").eq(contractor_id)
        )
        return resp.get("Items", [])

    def update_status(self, bid_id: str, status: str) -> Dict[str, Any]:
        resp = self.table.update_item(
            Key={"bid_id": bid_id},
            UpdateExpression="SET #s = :status",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":status": status},
            ReturnValues="ALL_NEW",
        )
        return resp.get("Attributes", {})
