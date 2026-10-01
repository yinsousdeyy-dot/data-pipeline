output "s3_ingestion_bucket" {
  value       = aws_s3_bucket.data_ingestion.id
  description = "S3 bucket for data ingestion"
}

output "s3_bucket_arn" {
  value       = aws_s3_bucket.data_ingestion.arn
  description = "ARN of S3 ingestion bucket"
}

output "emr_cluster_id" {
  value       = aws_emr_cluster.data_processing.id
  description = "EMR cluster ID for data processing"
}

output "emr_cluster_arn" {
  value       = aws_emr_cluster.data_processing.arn
  description = "ARN of EMR cluster"
}

output "state_machine_arn" {
  value       = aws_sfn_state_machine.pipeline_orchestration.arn
  description = "Step Functions state machine ARN for orchestration"
}

output "lambda_function_arn" {
  value       = aws_lambda_function.ingest_data.arn
  description = "ARN of Lambda ingestion function"
}

output "eventbridge_rule_name" {
  value       = aws_cloudwatch_event_rule.pipeline_schedule.name
  description = "EventBridge rule name for pipeline scheduling"
}

output "cloudwatch_log_group" {
  value       = aws_cloudwatch_log_group.pipeline_logs.name
  description = "CloudWatch log group for pipeline monitoring"
}

output "aws_account_id" {
  value       = data.aws_caller_identity.current.account_id
  description = "AWS account ID"
}

output "aws_region" {
  value       = var.aws_region
  description = "AWS region"
}
