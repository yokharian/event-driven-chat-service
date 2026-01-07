import dataclasses

import boto3
import botocore.client
from aws_lambda_powertools import Logger

logger = Logger()


@dataclasses.dataclass
class TableManager:
    dynamodb_endpoint_url: str
    client: botocore.client.BaseClient = dataclasses.field(init=False)

    def __post_init__(self):
        self.client = boto3.client("dynamodb", endpoint_url=self.dynamodb_endpoint_url)

    def create_table(self, *, table_name, table_hash_keys, secondary_indexes=None):
        sgi = [
            {
                "IndexName": idx_name,
                "KeySchema": [
                    {
                        "AttributeName": idx_field,
                        "KeyType": "HASH" if index == 0 else "RANGE",
                    }
                    for index, idx_field in enumerate(idx_fields)
                ],
                "Projection": {
                    "ProjectionType": "ALL",
                },
            }
            for idx_name, idx_fields in secondary_indexes or []
        ]
        creation_params = {
            "AttributeDefinitions": [
                {"AttributeName": key, "AttributeType": "S"} for key in table_hash_keys
            ],
            "TableName": table_name,
            "KeySchema": [
                {"AttributeName": key, "KeyType": "HASH" if idx == 0 else "RANGE"}
                for idx, key in enumerate(table_hash_keys)
            ],
            "BillingMode": "PAY_PER_REQUEST",
        }
        if secondary_indexes:
            keys = {
                field for idx_name, idx_fields in secondary_indexes or [] for field in idx_fields
            }
            creation_params["AttributeDefinitions"].extend(
                [{"AttributeName": key, "AttributeType": "S"} for key in keys]
            )
            creation_params["GlobalSecondaryIndexes"] = sgi
        self.client.create_table(**creation_params)

    def delete_table(self, table_name):
        self.client.delete_table(TableName=table_name)
