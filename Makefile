ACCOUNT_ID  := $(shell aws sts get-caller-identity --query Account --output text)
REGION      := $(or $(AWS_REGION),us-east-1)
ECR_REPO    := agent-benchmarks
IMAGE       := $(ACCOUNT_ID).dkr.ecr.$(REGION).amazonaws.com/$(ECR_REPO)
CLUSTER     := agent-benchmarks
SERVICE     := agent-benchmarks
TASK_FAMILY := agent-benchmarks
ROLE_ARN    := arn:aws:iam::$(ACCOUNT_ID):role/agent-benchmarks-task-role

.PHONY: setup build push deploy

setup:
	bash scripts/setup-aws.sh

build:
	docker build -t $(ECR_REPO):latest .

push: build
	aws ecr get-login-password --region $(REGION) | docker login --username AWS --password-stdin $(ACCOUNT_ID).dkr.ecr.$(REGION).amazonaws.com
	docker tag $(ECR_REPO):latest $(IMAGE):latest
	docker push $(IMAGE):latest

deploy: push
	# Register task definition
	aws ecs register-task-definition \
	  --family $(TASK_FAMILY) \
	  --network-mode awsvpc \
	  --requires-compatibilities FARGATE \
	  --cpu 256 --memory 512 \
	  --task-role-arn $(ROLE_ARN) \
	  --execution-role-arn arn:aws:iam::$(ACCOUNT_ID):role/ecsTaskExecutionRole \
	  --container-definitions "[{ \
	    \"name\": \"app\", \
	    \"image\": \"$(IMAGE):latest\", \
	    \"portMappings\": [{\"containerPort\": 8000}], \
	    \"environment\": [ \
	      {\"name\": \"AWS_REGION\", \"value\": \"$(REGION)\"}, \
	      {\"name\": \"DYNAMODB_TABLE\", \"value\": \"benchmark_runs\"} \
	    ], \
	    \"logConfiguration\": { \
	      \"logDriver\": \"awslogs\", \
	      \"options\": { \
	        \"awslogs-group\": \"/ecs/agent-benchmarks\", \
	        \"awslogs-region\": \"$(REGION)\", \
	        \"awslogs-stream-prefix\": \"ecs\" \
	      } \
	    } \
	  }]" > /dev/null
	# Force new deployment (creates service on first run if missing)
	aws ecs describe-services --cluster $(CLUSTER) --services $(SERVICE) --query 'services[0].status' --output text | grep -q ACTIVE && \
	  aws ecs update-service --cluster $(CLUSTER) --service $(SERVICE) --force-new-deployment > /dev/null || \
	  $(MAKE) _create-service
	@echo "Deployed. Check status: aws ecs describe-services --cluster $(CLUSTER) --services $(SERVICE)"

_create-service:
	$(eval SUBNETS := $(shell aws ec2 describe-subnets --filters Name=defaultForAz,Values=true --query 'Subnets[*].SubnetId' --output text --region $(REGION) | tr '\t' ','))
	$(eval SG := $(shell aws ec2 describe-security-groups --filters Name=group-name,Values=agent-benchmarks-sg --query 'SecurityGroups[0].GroupId' --output text --region $(REGION)))
	aws ecs create-service \
	  --cluster $(CLUSTER) \
	  --service-name $(SERVICE) \
	  --task-definition $(TASK_FAMILY) \
	  --launch-type FARGATE \
	  --desired-count 1 \
	  --network-configuration "awsvpcConfiguration={subnets=[$(SUBNETS)],securityGroups=[$(SG)],assignPublicIp=ENABLED}" \
	  > /dev/null
	@echo "Service created."
