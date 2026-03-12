variable "myregion" {
    description = "My AWS region"
    type = string
    default = "us-east-1"
}

variable "accountId" {
    description = "My AWS account ID"
    type = string
}

variable "lambda_function_name" {
    description = "Custom name for the lambda function"
    type = string
    default = "Biggest_Movers"
}

variable "endpoint_path" {
    description = "The GET endpoint path"
    type = string
    default = "movers"
}

variable "massive_api_key" {
  description = "Massive API key for stock data"
  type        = string
  sensitive   = true
}

variable "dynamodb_table_name" {
    description = "DynamoDB table name for daily winning stock"
    type        = string
    default     = "daily-winning-stock"
}