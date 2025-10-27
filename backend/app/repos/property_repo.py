from __future__ import annotations

from typing import Dict, Any, List

from boto3.dynamodb.conditions import Attr

from app.deps.dynamo import get_dynamo_resource, table_name


class PropertyRepo:
    def __init__(self):
        self.table = get_dynamo_resource().Table(table_name("properties"))

    def create_property(self, item: Dict[str, Any]) -> None:
        self.table.put_item(Item=item)

    def update_property(self, property_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        expressions = []
        names = {}
        values = {}
        for idx, (key, value) in enumerate(updates.items()):
            placeholder = f"#f{idx}"
            value_key = f":v{idx}"
            expressions.append(f"{placeholder} = {value_key}")
            names[placeholder] = key
            values[value_key] = value
        resp = self.table.update_item(
            Key={"property_id": property_id},
            UpdateExpression="SET " + ", ".join(expressions),
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
            ReturnValues="ALL_NEW",
        )
        return resp.get("Attributes", {})

    def get_property(self, property_id: str) -> Dict[str, Any]:
        resp = self.table.get_item(Key={"property_id": property_id})
        return resp.get("Item", {})

    def list_by_landlord(self, landlord_id: str) -> List[Dict[str, Any]]:
        resp = self.table.scan(
            FilterExpression=Attr("landlord_id").eq(landlord_id)
        )
        return resp.get("Items", [])

    def list_all(self) -> List[Dict[str, Any]]:
        resp = self.table.scan()
        return resp.get("Items", [])


class PropertyTenantRepo:
    def __init__(self):
        self.table = get_dynamo_resource().Table(table_name("property_tenants"))

    def add_member(self, property_id: str, tenant_id: str, email: str, status: str = "invited") -> None:
        self.table.put_item(
            Item={
                "property_id": property_id,
                "tenant_id": tenant_id,
                "email": email,
                "status": status,
            }
        )

    def update_status(self, property_id: str, tenant_id: str, status: str) -> None:
        self.table.update_item(
            Key={"property_id": property_id, "tenant_id": tenant_id},
            UpdateExpression="SET #s = :status",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":status": status},
        )

    def list_for_property(self, property_id: str) -> List[Dict[str, Any]]:
        resp = self.table.query(
            KeyConditionExpression="#pid = :pid",
            ExpressionAttributeNames={"#pid": "property_id"},
            ExpressionAttributeValues={":pid": property_id},
        )
        return resp.get("Items", [])

    def list_for_tenant(self, tenant_id: str) -> List[Dict[str, Any]]:
        resp = self.table.scan(
            FilterExpression=Attr("tenant_id").eq(tenant_id)
        )
        return resp.get("Items", [])
