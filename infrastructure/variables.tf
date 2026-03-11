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