############################################
# Data Pipeline Infrastructure with Terraform
# Components:
# - Ingestion & Storage
# - Compute & Processing
# - Orchestration & Scheduling
# - Security & Monitoring (IAM)
############################################

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ============================================
# 1. INGESTION & STORAGE
# ============================================

# S3 Bucket for Data Ingestion
resource "aws_s3_bucket" "data_ingestion" {
  bucket = "${var.project_name}-ingestion-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name        = "Data Ingestion Bucket"
    Environment = var.environment
    Component   = "Ingestion & Storage"
  }
}

# Enable versioning
resource "aws_s3_bucket_versioning" "data_ingestion" {
  bucket = aws_s3_bucket.data_ingestion.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Enable encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "data_ingestion" {
  bucket = aws_s3_bucket.data_ingestion.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# ============================================
# 2. COMPUTE & PROCESSING
# ============================================

# EMR Cluster for Data Processing
resource "aws_emr_cluster" "data_processing" {
  name              = "${var.project_name}-emr-cluster"
  release_label     = var.emr_release_label
  applications      = [{ name = "Spark" }, { name = "Hadoop" }]
  service_iam_role  = aws_iam_role.emr_service_role.arn
  ec2_instance_profile = aws_iam_instance_profile.emr_ec2_profile.arn

  ec2_attributes {
    instance_profile                  = aws_iam_instance_profile.emr_ec2_profile.arn
    security_group                    = aws_security_group.emr.id
    key_name                          = var.ec2_key_pair
    subnet_id                         = var.subnet_id
  }

  master_node_type      = var.emr_master_instance_type
  core_node_type        = var.emr_core_instance_type
  core_node_count       = var.emr_core_node_count

  tags = {
    Name        = "Data Processing Cluster"
    Environment = var.environment
    Component   = "Compute & Processing"
  }
}

# Security Group for EMR
resource "aws_security_group" "emr" {
  name        = "${var.project_name}-emr-sg"
  description = "Security group for EMR cluster"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "EMR Security Group"
  }
}

# ============================================
# 3. ORCHESTRATION & SCHEDULING
# ============================================

# Step Functions State Machine for Pipeline Orchestration
resource "aws_sfn_state_machine" "pipeline_orchestration" {
  name       = "${var.project_name}-pipeline-state-machine"
  role_arn   = aws_iam_role.sfn_role.arn
  definition = jsonencode({
    Comment = "Data Pipeline Orchestration"
    StartAt = "IngestData"
    States = {
      IngestData = {
        Type     = "Task"
        Resource = aws_lambda_function.ingest_data.arn
        Next     = "ProcessData"
      }
      ProcessData = {
        Type     = "Task"
        Resource = "arn:aws:states:::elasticmapreduce:addJobFlowSteps.sync"
        End      = true
      }
    }
  })

  tags = {
    Name        = "Pipeline Orchestration"
    Environment = var.environment
    Component   = "Orchestration & Scheduling"
  }
}

# EventBridge Rule for Scheduling
resource "aws_cloudwatch_event_rule" "pipeline_schedule" {
  name                = "${var.project_name}-pipeline-schedule"
  description         = "Trigger data pipeline on schedule"
  schedule_expression = var.pipeline_schedule_expression

  tags = {
    Name = "Pipeline Schedule"
  }
}

resource "aws_cloudwatch_event_target" "pipeline_target" {
  rule      = aws_cloudwatch_event_rule.pipeline_schedule.name
  arn       = aws_sfn_state_machine.pipeline_orchestration.arn
  role_arn  = aws_iam_role.eventbridge_role.arn
  target_id = "PipelineStateMachine"
}

# Lambda Function for Data Ingestion
resource "aws_lambda_function" "ingest_data" {
  filename      = "lambda_ingest.zip"
  function_name = "${var.project_name}-ingest-data"
  role          = aws_iam_role.lambda_role.arn
  handler       = "index.handler"
  runtime       = "python3.11"

  environment {
    variables = {
      S3_BUCKET = aws_s3_bucket.data_ingestion.id
    }
  }

  tags = {
    Name = "Data Ingestion Lambda"
  }
}

# ============================================
# 4. SECURITY & MONITORING (IAM)
# ============================================

# Data source for AWS account ID
data "aws_caller_identity" "current" {}

# IAM Role for EMR Service
resource "aws_iam_role" "emr_service_role" {
  name = "${var.project_name}-emr-service-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "elasticmapreduce.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "emr_service_policy" {
  role       = aws_iam_role.emr_service_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceRole"
}

# IAM Role for EMR EC2 Instances
resource "aws_iam_role" "emr_ec2_role" {
  name = "${var.project_name}-emr-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_instance_profile" "emr_ec2_profile" {
  name = "${var.project_name}-emr-ec2-profile"
  role = aws_iam_role.emr_ec2_role.name
}

resource "aws_iam_role_policy_attachment" "emr_ec2_policy" {
  role       = aws_iam_role.emr_ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceforEC2Role"
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "${var.project_name}-lambda-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "lambda_s3_policy" {
  name = "${var.project_name}-lambda-s3-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "s3:GetObject",
        "s3:PutObject"
      ]
      Resource = "${aws_s3_bucket.data_ingestion.arn}/*"
    }]
  })
}

# IAM Role for Step Functions
resource "aws_iam_role" "sfn_role" {
  name = "${var.project_name}-sfn-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "states.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "sfn_policy" {
  name = "${var.project_name}-sfn-policy"
  role = aws_iam_role.sfn_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction",
          "elasticmapreduce:AddJobFlowSteps",
          "elasticmapreduce:DescribeCluster"
        ]
        Resource = "*"
      }
    ]
  })
}

# IAM Role for EventBridge
resource "aws_iam_role" "eventbridge_role" {
  name = "${var.project_name}-eventbridge-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "events.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "eventbridge_policy" {
  name = "${var.project_name}-eventbridge-policy"
  role = aws_iam_role.eventbridge_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "states:StartExecution"
      ]
      Resource = aws_sfn_state_machine.pipeline_orchestration.arn
    }]
  })
}

# CloudWatch Log Group for Pipeline Monitoring
resource "aws_cloudwatch_log_group" "pipeline_logs" {
  name              = "/aws/data-pipeline/${var.project_name}"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "Pipeline Logs"
    Environment = var.environment
    Component   = "Security & Monitoring"
  }
}

# CloudWatch Alarms for Monitoring
resource "aws_cloudwatch_metric_alarm" "emr_unhealthy" {
  alarm_name          = "${var.project_name}-emr-unhealthy-nodes"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "UnhealthyNodes"
  namespace           = "AWS/ElasticMapReduce"
  period              = 300
  statistic           = "Average"
  threshold           = 0
  alarm_description   = "Alert when EMR cluster has unhealthy nodes"
}

# ============================================
# OUTPUTS
# ============================================

output "s3_ingestion_bucket" {
  value       = aws_s3_bucket.data_ingestion.id
  description = "S3 bucket for data ingestion"
}

output "emr_cluster_id" {
  value       = aws_emr_cluster.data_processing.id
  description = "EMR cluster ID for data processing"
}

output "state_machine_arn" {
  value       = aws_sfn_state_machine.pipeline_orchestration.arn
  description = "Step Functions state machine ARN for orchestration"
}
