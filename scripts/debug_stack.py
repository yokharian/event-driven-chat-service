import os

import boto3

endpoint_url = os.environ.get("AWS_ENDPOINT_URL", "http://localhost:4566")
print(f"Connecting to {endpoint_url}")

cf = boto3.client(
    "cloudformation",
    endpoint_url=endpoint_url,
    region_name="us-east-1",
    aws_access_key_id="test",
    aws_secret_access_key="test",
)

stack_name = "chat-service-stack"

try:
    stacks = cf.describe_stacks(StackName=stack_name)
    print(f"Stack Status: {stacks["Stacks"][0]["StackStatus"]}")

    response = cf.describe_stack_events(StackName=stack_name)
    print("Recent Events:")
    for event in response["StackEvents"][:10]:
        print(
            f"  {event["LogicalResourceId"]}: {event["ResourceStatus"]} - {event.get("ResourceStatusReason", "")}"
        )

except Exception as e:
    print(f"Error: {e}")
