terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

locals {
  prefix = "${var.table_prefix}_${var.stage}"
}

resource "aws_dynamodb_table" "chat_messages" {
  name         = "${local.prefix}_chat_messages"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "thread_id"
  range_key    = "timestamp"

  attribute {
    name = "thread_id"
    type = "S"
  }
  attribute {
    name = "timestamp"
    type = "S"
  }
}

resource "aws_dynamodb_table" "incidents" {
  name         = "${local.prefix}_incidents"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"

  attribute { name = "user_id" type = "S" }
}

resource "aws_dynamodb_table" "jobs" {
  name         = "${local.prefix}_jobs"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"

  attribute { name = "user_id" type = "S" }
}

data "aws_iam_policy_document" "ddb_access" {
  statement {
    actions = [
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:GetItem",
      "dynamodb:Query",
      "dynamodb:Scan"
    ]
    resources = [
      aws_dynamodb_table.chat_messages.arn,
      aws_dynamodb_table.incidents.arn,
      aws_dynamodb_table.jobs.arn
    ]
  }
}

resource "aws_iam_policy" "app_ddb_policy" {
  name   = "${local.prefix}-ddb-policy"
  policy = data.aws_iam_policy_document.ddb_access.json
}

output "table_names" {
  value = {
    chat_messages = aws_dynamodb_table.chat_messages.name
    incidents     = aws_dynamodb_table.incidents.name
    jobs          = aws_dynamodb_table.jobs.name
  }
}
