output "endpoint_url" {
  description = "Invoke URL for the API Gateway endpoint"
  value = "https://${aws_api_gateway_rest_api.movement_rest_api.id}.execute-api.${var.myregion}.amazonaws.com/${aws_api_gateway_stage.movers_deploy.stage_name}/${var.endpoint_path}"
}

output "dynamodb_table_name" {
  description = "DynamoDB table name storing daily winner"
  value       = aws_dynamodb_table.daily_winners.name
}

output "dynamodb_table_arn" {
  description = "DynamoDB table ARN storing daily winner"
  value       = aws_dynamodb_table.daily_winners.arn
}