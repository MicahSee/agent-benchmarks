#!/bin/bash
# Provisions all AWS resources needed to run agent-benchmarks.
# Run once: bash scripts/setup-aws.sh
set -euo pipefail

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=${AWS_REGION:-us-east-1}
ECR_REPO="agent-benchmarks"
TABLE_NAME="benchmark_runs"
CLUSTER_NAME="agent-benchmarks"
SERVICE_NAME="agent-benchmarks"
TASK_FAMILY="agent-benchmarks"
ROLE_NAME="agent-benchmarks-task-role"
SG_NAME="agent-benchmarks-sg"

echo "==> Account: $ACCOUNT_ID  Region: $REGION"

# ECR
echo "==> Creating ECR repository..."
aws ecr create-repository --repository-name $ECR_REPO --region $REGION 2>/dev/null || echo "    (already exists)"

# DynamoDB
echo "==> Creating DynamoDB table..."
aws dynamodb create-table \
  --table-name $TABLE_NAME \
  --attribute-definitions \
    AttributeName=run_id,AttributeType=S \
    AttributeName=benchmark,AttributeType=S \
    AttributeName=timestamp,AttributeType=S \
  --key-schema AttributeName=run_id,KeyType=HASH \
  --global-secondary-indexes '[{
    "IndexName": "benchmark-timestamp-index",
    "KeySchema": [
      {"AttributeName": "benchmark","KeyType": "HASH"},
      {"AttributeName": "timestamp","KeyType": "RANGE"}
    ],
    "Projection": {"ProjectionType": "ALL"}
  }]' \
  --billing-mode PAY_PER_REQUEST \
  --region $REGION 2>/dev/null || echo "    (already exists)"

# api_keys DynamoDB table
echo "==> Creating api_keys DynamoDB table..."
aws dynamodb create-table \
  --table-name api_keys \
  --attribute-definitions \
    AttributeName=key_hash,AttributeType=S \
    AttributeName=user_id,AttributeType=S \
    AttributeName=created_at,AttributeType=S \
  --key-schema AttributeName=key_hash,KeyType=HASH \
  --global-secondary-indexes '[{
    "IndexName": "user-index",
    "KeySchema": [
      {"AttributeName": "user_id","KeyType": "HASH"},
      {"AttributeName": "created_at","KeyType": "RANGE"}
    ],
    "Projection": {"ProjectionType": "ALL"}
  }]' \
  --billing-mode PAY_PER_REQUEST \
  --region $REGION 2>/dev/null || echo "    (already exists)"

# IAM task role
echo "==> Creating ECS task IAM role..."
aws iam create-role \
  --role-name $ROLE_NAME \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ecs-tasks.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }' 2>/dev/null || echo "    (already exists)"

aws iam put-role-policy \
  --role-name $ROLE_NAME \
  --policy-name dynamodb-access \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [{
      \"Effect\": \"Allow\",
      \"Action\": [
        \"dynamodb:GetItem\",
        \"dynamodb:PutItem\",
        \"dynamodb:Query\",
        \"dynamodb:Scan\"
      ],
      \"Resource\": [
        \"arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/${TABLE_NAME}\",
        \"arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/${TABLE_NAME}/index/*\",
        \"arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/api_keys\",
        \"arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/api_keys/index/*\"
      ]
    }]
  }"

# ECS cluster
echo "==> Creating ECS cluster..."
aws ecs create-cluster --cluster-name $CLUSTER_NAME --region $REGION > /dev/null

# Security group
echo "==> Creating security group..."
VPC_ID=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text --region $REGION)
SG_ID=$(aws ec2 create-security-group \
  --group-name $SG_NAME \
  --description "agent-benchmarks API" \
  --vpc-id $VPC_ID \
  --region $REGION \
  --query GroupId --output text 2>/dev/null) || \
  SG_ID=$(aws ec2 describe-security-groups \
    --filters Name=group-name,Values=$SG_NAME --query 'SecurityGroups[0].GroupId' --output text --region $REGION)

aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp --port 8000 --cidr 0.0.0.0/0 \
  --region $REGION 2>/dev/null || true

echo ""
echo "==> Done. Resources created:"
echo "    ECR:      ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO}"
echo "    DynamoDB: ${TABLE_NAME}"
echo "    Cluster:  ${CLUSTER_NAME}"
echo "    Role ARN: arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"
echo "    SG ID:    ${SG_ID}"
echo ""
echo "Next: make build && make push && make deploy"
