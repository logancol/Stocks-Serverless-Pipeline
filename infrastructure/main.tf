terraform {
    required_providers {
        aws = {
            source = "hashicorp/aws"
            version = "4.47.0"
        }
    }
}

provider "aws" {
    region = "us-east-1"
}

resource "aws_lambda_function" "movement_lambda" {
    function_name = var.lambda_function_name
    runtime = "python3.11"
    role = aws_iam_role.lambda_role_arn
    handler = "lambda.lambda_handler"
    file_name = "deployment_package.zip"
    depends_on = [
        aws_iam_role_policy_attachment.lambda_logs,
        aws_cloudwatch_log_group.example,
    ]
}

resource "aws_cloudwatch_log_group" "movement" {
    name = "/aws/lambda/${var.lambda_function_name}"
    retention_in_days = 7
}

resource "aws_iam_policy" "lambda_logging" {
  name        = "lambda_logging"
  path        = "/"
  description = "IAM policy for logging from the lambda function"

  policy = <<EOF

{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
    role = aws_iam_role.lambda_role.name
    policy_arn = aws_iam_policy.lamda_logging.arn
}

resource "aws_iam_role" "lambda_role" {
  name = "lambda_role"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
}

resource "aws_api_gateway_rest_api" "movement_rest_api" {
    name = "movement_rest_api"
}

resource "aws_api_gateway_resource" "api_resource" {
    rest_api_id = aws_api_gateway_rest_api.movement_rest_api.id
    parent_id = aws_api_gateway_rest_api.example_api.root_resource_id
    path_part = var.endpoint_path
}

resource "aws_api_gateway_method" "movers_get" {
    rest_api_id = aws_api_gateway_rest_api.movement_rest_api.id
    resource_id = awsl_api_gateway_resource.api_resource.id
    http_method = "GET"
    authorization = "NONE"
}

resource "aws_api_gateway_integration" "integration" {
    rest_api_id = aws_api_gateway_rest_api.movement_rest_api.id
    resource_id = aws_api_gateway_resource.api_resource.id
    http_method = aws_api_gateway_method.movers_get.http_method
    integration_http_method = "POST"
    type = "AWS_PROXY"
    uri = aws_lambda_function.movement_lambda.invoke_arn
}

resource "aws_lambda_permission" "apigw_lambda" {
    statement_id = "AllowExecutionFromGateway"
    action = "lambda:InvokeFunction"
    function_name = aws_lambda_function.movement_lambda.function_name
    principal = "apigateway.amazonaws.com"
    source_arn = "arn:aws:execute-api:${var.myregion}:${var.accountId}:${aws_api_gateway_rest_api.movement_rest_api}/*/${
    aws_api_gateway_method.movers_get.http_method}${aws_api_gateway_resource.api_resource.path}"
}

resource "aws_api_gateway_deployment" "movers_deploy" {
    rest_api_id = aws_api_gateway_rest_api.movement_rest_api.id

    triggers = {
        redeployment = sha1(jsonencode(aws_api_gateway_rest_api.movement_rest_api.body))
    }

    lifecycle {
        create_before_destroy = true
    }
    depends_on = [aws_api_gateway_method.movers_get, aws_api_gateway_integration.integration]
}

resource "aws_api_gateway_stage" "movers_deploy" {
    deployment_id = aws_api_gateway_deployment.movers_deploy.id
    rest_api_id = aws_api_gateway_rest_api.movement_rest_api
    stage_name = "prod"
}