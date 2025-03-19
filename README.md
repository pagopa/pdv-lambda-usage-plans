# API Gateway Usage Plans Lambda

This Lambda function collects API Gateway usage plan metrics and publishes them to CloudWatch as custom metrics.

## Features

- Retrieves all API Gateway usage plans
- Collects hourly usage metrics for each API key
- Publishes metrics to CloudWatch with dimensions for UsagePlan and APIKey
- Handles error cases gracefully

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LOG_LEVEL` | Logging level (INFO, DEBUG, ERROR) | INFO |
| `APIGATEWAY_METRICS_NAMESPACE` | CloudWatch namespace for metrics | ApiGateway/UsagePlans |

## Development

### Local Development

To run the function locally:

```bash
python src/index.py
```

### Deployment

The function is automatically packaged and published as a GitHub release when changes are pushed to the main branch. The package can be downloaded from the releases page and deployed to AWS Lambda.

## GitHub Actions

This repository uses GitHub Actions for CI/CD:

- **Build and Publish**: Creates a deployment package and publishes it as a GitHub release

## Installation

1. Download the latest `lambda-usage-plans.zip` from GitHub releases
2. Create a new Lambda function in AWS
3. Upload the zip file as the function code
4. Configure the environment variables
5. Set up appropriate IAM permissions:
   - API Gateway read access
   - CloudWatch metrics write access
6. Set up a scheduled EventBridge rule to trigger the Lambda function hourly