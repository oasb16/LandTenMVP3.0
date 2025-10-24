from typing import Optional, Dict
from app.deps.dynamo import get_dynamo_resource, table_name


class ProfileRepo:
    def __init__(self):
        self.table = get_dynamo_resource().Table(table_name("profiles"))

    def upsert_profile(self, user_id: str, persona: str) -> Dict[str, str]:
        item = {"user_id": user_id, "persona": persona}
        self.table.put_item(Item=item)
        return item

    def get_profile(self, user_id: str) -> Optional[Dict[str, str]]:
        resp = self.table.get_item(Key={"user_id": user_id})
        return resp.get("Item")
