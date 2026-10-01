variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "data-pipeline"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "emr_release_label" {
  description = "EMR release label"
  type        = string
  default     = "emr-6.13.0"
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

variable "emr_core_node_count" {
  description = "Number of EMR core nodes"
  type        = number
  default     = 2
}

variable "vpc_id" {
  description = "VPC ID for EMR cluster"
  type        = string
}

variable "subnet_id" {
  description = "Subnet ID for EMR cluster"
  type        = string
}

variable "ec2_key_pair" {
  description = "EC2 key pair name for SSH access"
  type        = string
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access EMR cluster"
  type        = list(string)
  default     = ["10.0.0.0/8"]
}

variable "pipeline_schedule_expression" {
  description = "EventBridge cron schedule for pipeline"
  type        = string
  default     = "cron(0 2 * * ? *)"
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}
