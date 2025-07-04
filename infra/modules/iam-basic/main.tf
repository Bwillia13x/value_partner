resource "aws_iam_role" "lakehouse_read" {
  name               = "lakehouse-read-role"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
}

data "aws_iam_policy_document" "assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_policy" "lakehouse_read" {
  name   = "lakehouse-read-policy"
  policy = data.aws_iam_policy_document.read_only.json
}

data "aws_iam_policy_document" "read_only" {
  statement {
    effect = "Allow"
    actions = ["s3:GetObject", "s3:ListBucket"]
    resources = [
      var.lakehouse_bucket_arn,
      "${var.lakehouse_bucket_arn}/*",
    ]
  }
}

resource "aws_iam_role_policy_attachment" "attach" {
  role       = aws_iam_role.lakehouse_read.name
  policy_arn = aws_iam_policy.lakehouse_read.arn
}