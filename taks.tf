############################################
# Data Pipeline Infrastructure
# Components:
# - Ingestion & Storage
# - Compute & Processing
# - Orchestration & Scheduling
# - Security & Monitoring (IAM)
############################################

terraform {
  required_version = ">= 1.3.0"

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

data "aws_caller_identity" "current" {}

# ============================================
# 1. INGESTION & STORAGE
# ============================================

resource "aws_s3_bucket" "raw_data" {
  bucket = "${var.project_name}-raw-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name        = "raw-data"
    Environment = var.environment
    Project     = var.project_name
    Component   = "Ingestion & Storage"
  }
}

resource "aws_s3_bucket_versioning" "raw_data" {
  bucket = aws_s3_bucket.raw_data.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "raw_data" {
  bucket = aws_s3_bucket.raw_data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# ============================================
# 2. COMPUTE & PROCESSING
# ============================================

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
    Name      = "${var.project_name}-emr-sg"
    Project   = var.project_name
    Component = "Compute & Processing"
  }
}

resource "aws_iam_role" "emr_service_role" {
  name = "${var.project_name}-emr-service-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = "sts:AssumeRole"
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

resource "aws_iam_role" "emr_ec2_role" {
  name = "${var.project_name}-emr-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = "sts:AssumeRole"
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

resource "aws_emr_cluster" "processing" {
  name          = "${var.project_name}-emr-cluster"
  release_label = var.emr_release_label
  applications  = ["Spark", "Hadoop"]

  service_role = aws_iam_role.emr_service_role.arn

  ec2_attributes {
    instance_profile = aws_iam_instance_profile.emr_ec2_profile.arn
    subnet_id       = var.subnet_id
    emr_managed_master_security_group = aws_security_group.emr.id
    emr_managed_slave_security_group  = aws_security_group.emr.id
  }

  master_instance_type = var.emr_master_instance_type
  core_instance_type   = var.emr_core_instance_type
  core_instance_count  = var.emr_core_instance_count

  tags = {
    Name        = "${var.project_name}-emr-cluster"
    Environment = var.environment
    Project     = var.project_name
    Component   = "Compute & Processing"
  }
}

# ============================================
# 3. ORCHESTRATION & SCHEDULING
# ============================================

resource "aws_iam_role" "lambda_role" {
  name = "${var.project_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = "sts:AssumeRole"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "lambda_s3_access" {
  name = "${var.project_name}-lambda-s3-access"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ]
      Resource = [
        aws_s3_bucket.raw_data.arn,
        "${aws_s3_bucket.raw_data.arn}/*"
      ]
    }]
  })
}

resource "aws_lambda_function" "ingest_data" {
  function_name = "${var.project_name}-ingest-data"
  role          = aws_iam_role.lambda_role.arn
  handler       = "index.handler"
  runtime       = "python3.11"
  filename      = "lambda_ingest.zip"

  source_code_hash = filebase64sha256("lambda_ingest.zip")

  environment {
    variables = {
      S3_BUCKET = aws_s3_bucket.raw_data.id
    }
  }

  tags = {
    Name      = "${var.project_name}-ingest-data"
    Project   = var.project_name
    Component = "Orchestration & Scheduling"
  }
}

resource "aws_iam_role" "sfn_role" {
  name = "${var.project_name}-sfn-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = "sts:AssumeRole"
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
    Statement = [{
      Effect = "Allow"
      Action = [
        "lambda:InvokeFunction",
        "elasticmapreduce:AddJobFlowSteps",
        "elasticmapreduce:DescribeCluster",
        "states:StartExecution"
      ]
      Resource = "*"
    }]
  })
}

resource "aws_sfn_state_machine" "pipeline" {
  name     = "${var.project_name}-pipeline"
  role_arn = aws_iam_role.sfn_role.arn

  definition = jsonencode({
    StartAt = "Ingest"
    States = {
      Ingest = {
        Type     = "Task"
        Resource = aws_lambda_function.ingest_data.arn
        Next     = "Process"
      }
      Process = {
        Type     = "Task"
        Resource = "arn:aws:states:::elasticmapreduce:addStep.sync"
        Parameters = {
          ClusterId = aws_emr_cluster.processing.id
          Step = {
            Name = "spark-processing-step"
            ActionOnFailure = "TERMINATE_CLUSTER"
            HadoopJarStep = {
              Jar = "command-runner.jar"
              Args = ["spark-submit", "s3://${aws_s3_bucket.raw_data.bucket}/scripts/process.py"]
            }
          }
        }
        End = true
      }
    }
  })

  tags = {
    Name        = "${var.project_name}-pipeline"
    Environment = var.environment
    Project     = var.project_name
    Component   = "Orchestration & Scheduling"
  }
}

resource "aws_cloudwatch_event_rule" "pipeline_schedule" {
  name                = "${var.project_name}-pipeline-schedule"
  description         = "Run pipeline on a schedule"
  schedule_expression = var.pipeline_schedule_expression

  tags = {
    Name      = "${var.project_name}-pipeline-schedule"
    Project   = var.project_name
    Component = "Orchestration & Scheduling"
  }
}

resource "aws_cloudwatch_event_target" "pipeline_target" {
  rule      = aws_cloudwatch_event_rule.pipeline_schedule.name
  arn       = aws_sfn_state_machine.pipeline.arn
  role_arn  = aws_iam_role.sfn_role.arn
  target_id = "PipelineTarget"
}

# ============================================
# 4. SECURITY & MONITORING (IAM)
# ============================================

resource "aws_iam_role" "monitoring_role" {
  name = "${var.project_name}-monitoring-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = "sts:AssumeRole"
      Principal = {
        Service = "cloudwatch.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_policy" "monitoring_policy" {
  name = "${var.project_name}-monitoring-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "cloudwatch:PutMetricData",
        "ec2:Describe*",
        "elasticmapreduce:DescribeCluster"
      ]
      Resource = "*"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "monitoring_attach" {
  role       = aws_iam_role.monitoring_role.name
  policy_arn = aws_iam_policy.monitoring_policy.arn
}

resource "aws_cloudwatch_log_group" "pipeline_logs" {
  name              = "/aws/data-pipeline/${var.project_name}"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "${var.project_name}-pipeline-logs"
    Environment = var.environment
    Project     = var.project_name
    Component   = "Security & Monitoring"
  }
}

resource "aws_cloudwatch_metric_alarm" "emr_unhealthy_nodes" {
  alarm_name          = "${var.project_name}-emr-unhealthy-nodes"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "UnhealthyNodes"
  namespace           = "AWS/ElasticMapReduce"
  period              = 300
  statistic           = "Average"
  threshold           = 0
  alarm_description   = "Alert when EMR has unhealthy nodes"

  tags = {
    Name      = "${var.project_name}-emr-unhealthy-nodes"
    Project   = var.project_name
    Component = "Security & Monitoring"
  }
}

# ============================================
# VARIABLES
# ============================================

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name prefix for all resources"
  type        = string
  default     = "data-pipeline"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

variable "vpc_id" {
  description = "VPC id"
  type        = string
}

variable "subnet_id" {
  description = "Subnet id for EMR and networking"
  type        = string
}

variable "allowed_cidr_blocks" {
  description = "CIDR ranges allowed for ingest and cluster access"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "emr_release_label" {
  description = "EMR release label"
  type        = string
  default     = "emr-6.15.0"
}

variable "emr_master_instance_type" {
  description = "EMR master node instance type"
  type        = string
  default     = "m5.xlarge"
}

variable "emr_core_instance_type" {
  description = "EMR core node instance type"
  type        = string
  default     = "m5.xlarge"
}

variable "emr_core_instance_count" {
  description = "Number of EMR core nodes"
  type        = number
  default     = 2
}

variable "pipeline_schedule_expression" {
  description = "Cron or rate expression for the pipeline trigger"
  type        = string
  default     = "cron(0 2 * * ? *)"
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

# ============================================
# OUTPUTS
# ============================================

output "raw_bucket_name" {
  value       = aws_s3_bucket.raw_data.bucket
  description = "Name of the raw data bucket"
}

output "emr_cluster_id" {
  value       = aws_emr_cluster.processing.id
  description = "EMR cluster identifier"
}

output "pipeline_state_machine_arn" {
  value       = aws_sfn_state_machine.pipeline.arn
  description = "Step Functions orchestration ARN"
}

output "log_group_name" {
  value       = aws_cloudwatch_log_group.pipeline_logs.name
  description = "Central log group for pipeline monitoring"
}
