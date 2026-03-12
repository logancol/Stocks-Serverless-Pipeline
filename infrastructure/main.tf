# aws provider version
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.0"
    }
  }
}

# region
provider "aws" {
  region = "us-east-1"
}

# defines lambda that computes our daily winner
resource "aws_lambda_function" "movement_lambda" {
  environment {
    variables = {
      MASSIVE_API_KEY     = var.massive_api_key
      DYNAMODB_TABLE_NAME = aws_dynamodb_table.daily_winners.name
    }
  }
  function_name    = var.lambda_function_name
  runtime          = "python3.11"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda.lambda_handler"
  filename         = "deployment_package.zip"
  source_code_hash = filebase64sha256("deployment_package.zip")
  timeout          = 720
  depends_on = [
    aws_iam_role_policy_attachment.lambda_logs,
    aws_cloudwatch_log_group.movement,
  ]
}

# creates log group for cloudwatch and defines log retention
resource "aws_cloudwatch_log_group" "movement" {
  name              = "/aws/lambda/${var.lambda_function_name}"
  retention_in_days = 7
}

# policy that allows creating log groups, streams, and adding logs
resource "aws_iam_policy" "lambda_logging" {
  name        = "lambda_logging"
  path        = "/"
  description = "IAM policy for logging from the lambda function"

  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Action" : [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        "Resource" : "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# attaches logging policy to lambda exec role
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_logging.arn
}

# IAM policy that allows reading from and writing to the dynamo db
resource "aws_iam_policy" "lambda_dynamodb" {
  name        = "lambda_dynamodb"
  path        = "/"
  description = "IAM policy for DynamoDB access from Lambda"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:GetItem",
          "dynamodb:Scan",
          "dynamodb:Query"
        ]
        # above permissions are scoped to the daily winners table only
        Resource = aws_dynamodb_table.daily_winners.arn
      }
    ]
  })
}

# atttaches dynamo db policy to the lambda exec role
resource "aws_iam_role_policy_attachment" "lambda_dynamodb" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_dynamodb.arn
}

# IAM role assumed by lambda at runtime
resource "aws_iam_role" "lambda_role" {
  name = "lambda_role"

  assume_role_policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Principal" : {
          "Service" : "lambda.amazonaws.com"
        },
        "Action" : "sts:AssumeRole"
      }
    ]
  })
}

# creates container (shell) for rest api gateway
resource "aws_api_gateway_rest_api" "movement_rest_api" {
  name = "movement_rest_api"
}

# adds a path under the route (/movers)
resource "aws_api_gateway_resource" "api_resource" {
  rest_api_id = aws_api_gateway_rest_api.movement_rest_api.id
  parent_id   = aws_api_gateway_rest_api.movement_rest_api.root_resource_id
  path_part   = var.endpoint_path
}

# adds a get method to movers
resource "aws_api_gateway_method" "movers_get" {
  rest_api_id   = aws_api_gateway_rest_api.movement_rest_api.id
  resource_id   = aws_api_gateway_resource.api_resource.id
  http_method   = "GET"
  authorization = "NONE"
}

# tells api gateway that movers_get should invoke the api lambda (defined below)
resource "aws_api_gateway_integration" "integration" {
  rest_api_id             = aws_api_gateway_rest_api.movement_rest_api.id
  resource_id             = aws_api_gateway_resource.api_resource.id
  http_method             = aws_api_gateway_method.movers_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.movers_api_lambda.invoke_arn
}

# givest the gateway permission to call the lambda
resource "aws_lambda_permission" "apigw_lambda" {
  statement_id  = "AllowExecutionFromGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.movers_api_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.movement_rest_api.execution_arn}/*/${aws_api_gateway_method.movers_get.http_method}${aws_api_gateway_resource.api_resource.path}"
}

# creates a deployable snapshot of the the rest api config, redeploying when the linked resources change
resource "aws_api_gateway_deployment" "movers_deploy" {
  rest_api_id = aws_api_gateway_rest_api.movement_rest_api.id

  triggers = {
    redeployment = sha1(jsonencode({
      resource_id = aws_api_gateway_resource.api_resource.id
      method_id   = aws_api_gateway_method.movers_get.id
      integration = aws_api_gateway_integration.integration.id
    }))
  }

  lifecycle {
    create_before_destroy = true
  }
  depends_on = [aws_api_gateway_method.movers_get, aws_api_gateway_integration.integration]
}

resource "aws_api_gateway_stage" "movers_deploy" {
  deployment_id = aws_api_gateway_deployment.movers_deploy.id
  rest_api_id   = aws_api_gateway_rest_api.movement_rest_api.id
  stage_name    = "prod"
}

# creates lambda which gets the winners, linked to the gateway above
resource "aws_lambda_function" "movers_api_lambda" {
  environment {
    variables = {
      DYNAMODB_TABLE_NAME = aws_dynamodb_table.daily_winners.name
    }
  }
  function_name    = "MoversApi"
  runtime          = "python3.11"
  role             = aws_iam_role.lambda_role.arn
  handler          = "api_lambda.lambda_handler"
  filename         = "deployment_package.zip"
  source_code_hash = filebase64sha256("deployment_package.zip")
  timeout          = 10
  depends_on = [
    aws_iam_role_policy_attachment.lambda_logs,
    aws_iam_role_policy_attachment.lambda_dynamodb,
  ]
}

# creates an event rule for running the movement lambda at 22 UTC on trading days
resource "aws_cloudwatch_event_rule" "daily_mover" {
  name                = "daily_mover_schedule"
  description         = "Daily job to compute and store biggest mover"
  schedule_expression = "cron(0 22 ? * MON-FRI *)"
}

# connects the schedule to the lambda
resource "aws_cloudwatch_event_target" "daily_mover_target" {
  rule      = aws_cloudwatch_event_rule.daily_mover.name
  target_id = "movement_lambda"
  arn       = aws_lambda_function.movement_lambda.arn
}

# gives eventbridge perms to invoke the movement calculation lambda
resource "aws_lambda_permission" "eventbridge_invoke" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.movement_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_mover.arn
}

# creates bucket for the s3 site
resource "aws_s3_bucket" "frontend" {
  bucket = "pennymac-stockserverless-frontend-3214562"
}

# configures static hosting with entry file index.html
resource "aws_s3_bucket_website_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "index.html"
  }
}

# disables protections to make bucket publicly readable
resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

# makes objects in bucket readable from browser
resource "aws_s3_bucket_policy" "frontend_public" {
  bucket = aws_s3_bucket.frontend.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicRead"
        Effect    = "Allow"
        Principal = "*"
        Action    = ["s3:GetObject"]
        Resource  = ["${aws_s3_bucket.frontend.arn}/*"]
      }
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.frontend]
}

# prints the url after apply for easy nav
output "frontend_website_url" {
  value = aws_s3_bucket_website_configuration.frontend.website_endpoint
}
