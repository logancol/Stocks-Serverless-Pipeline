
resource "aws_dynamodb_table" "daily_winners" {
	name         = var.dynamodb_table_name
	billing_mode = "PAY_PER_REQUEST"

	hash_key = "date"

	attribute {
		name = "date"
		type = "S"
	}
}

