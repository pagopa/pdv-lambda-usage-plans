import boto3
import datetime
from datetime import timedelta
import logging
import os


logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))


CW_NAMESPACE = os.environ.get('APIGATEWAY_METRICS_NAMESPACE', 'ApiGateway/UsagePlans')

apigw_client = boto3.client('apigateway')
cloudwatch = boto3.client('cloudwatch')

def get_usage_plans() -> list:
    """Retrieve all usage plans from API Gateway."""
    usage_plans = []
    paginator = apigw_client.get_paginator('get_usage_plans')
    for page in paginator.paginate():
        usage_plans.extend(page['items'])
    return usage_plans


def get_usage_for_date(usage_plan_id: str, key_id: str, start_date: datetime.date, end_date: datetime.date) -> dict:
    """Get usage for a specific date range"""
    response = apigw_client.get_usage(
        usagePlanId=usage_plan_id,
        keyId=key_id,
        startDate=start_date.strftime('%Y-%m-%d'),
        endDate=end_date.strftime('%Y-%m-%d')
    )
    return response.get('items', {})

def publish_metric(value: float, plan_name: str, api_key: str, metric_name: str='Usage') -> None:
    """Publish a single metric to CloudWatch"""
    cloudwatch.put_metric_data(
        Namespace=CW_NAMESPACE,
        MetricData=[{
            'MetricName': metric_name,
            'Value': float(value),
            'Unit': 'Count',
            'StorageResolution': 60,
            'Dimensions': [
                {'Name': 'UsagePlan', 'Value': plan_name},
                {'Name': 'APIKey', 'Value': api_key}
            ]
        }]
    )


def get_previous_usage(plan_name, api_key, timestamp) -> float:
    """Get the last known cumulative usage value before this timestamp"""
    try:
        response = cloudwatch.get_metric_data(
            MetricDataQueries=[{
                'Id': 'usage',
                'MetricStat': {
                    'Metric': {
                        'Namespace': CW_NAMESPACE,
                        'MetricName': 'Usage',  # Separate metric for cumulative values
                        'Dimensions': [
                            {'Name': 'UsagePlan', 'Value': plan_name},
                            {'Name': 'APIKey', 'Value': api_key}
                        ]
                    },
                    'Period': 3600,
                    'Stat': 'Maximum'
                }
            }],
            StartTime=timestamp - timedelta(hours=2),
            EndTime=timestamp
        )
        
        values = response['MetricDataResults'][0]['Values']
        return values[-1] if values else 0
    except Exception as e:
        logger.error(f"Error getting previous usage for {plan_name} - {api_key}: {str(e)}")
        return 0

def lambda_handler(event: dict, context) -> dict:
    
    # Get current time and calculate the previous hour
    now = datetime.datetime.utcnow()
    # Round down to the nearest hour
    current_hour = now.replace(minute=0, second=0, microsecond=0)
    previous_hour = current_hour - timedelta(hours=1)
    
    # Get all usage plans
    usage_plans = get_usage_plans()
    
    for plan in usage_plans:
        plan_id = plan['id']
        plan_name = plan['name']
        
        try:
            keys = apigw_client.get_usage_plan_keys(usagePlanId=plan_id)
            
            for key in keys.get('items', []):
                key_id = key['id']
                key_name = key['name']
                
                # Get usage data for the current day
                usage_data = get_usage_for_date(
                    plan_id,
                    key_id,
                    previous_hour.date(),
                    current_hour.date()
                )
                
                if not usage_data:                    
                    logger.debug(f"No usage data found for {plan_name} - {key_name}")
                    publish_metric(0, plan_name, key_name)
                    continue
                
                for day_data in usage_data:
                
                    try:
                        current_usage = usage_data[day_data][0][0]
                    except IndexError:  
                        logger.error(f"Error getting current usage for {plan_name} - {key_name}")
                        current_usage = None

                    if current_usage is not None:
                        # Get the previous hour's cumulative usage if current_usage is greater than 0.
                        # If the current usage is 0 the previous usage can be ignored.
                        previous_usage = get_previous_usage(
                            plan_name,
                            key_name,
                            previous_hour
                        ) if current_usage > 0 else 0
                        
                        # Calculate the actual requests in this hour
                        hourly_requests = current_usage - previous_usage if current_usage > previous_usage else 0
                        
                        # Store the hourly difference
                        publish_metric(
                            hourly_requests,
                            plan_name,
                            key_name
                        )
                        
                        
        except Exception as e:
            logger.error(f"Error processing usage data for {plan_name}: {str(e)}")
            raise e
    
    return {
        'statusCode': 200,
        'body': 'Successfully processed API usage metrics'
    }


if __name__ == "__main__":
    lambda_handler({}, {})
