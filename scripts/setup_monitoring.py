"""
Setup monitoring and alerting for production
- Configure CloudWatch logs
- Set up error alerts
- Configure performance monitoring
"""

import boto3


def setup_cloudwatch_logs():
    """Create CloudWatch log groups for application."""
    logs = boto3.client("logs")
    log_groups = [
        "/landten/backend/application",
        "/landten/backend/errors",
        "/landten/backend/performance",
    ]

    for group in log_groups:
        try:
            logs.create_log_group(logGroupName=group)
            print(f"✓ Created log group: {group}")
        except logs.exceptions.ResourceAlreadyExistsException:
            print(f"✓ Log group exists: {group}")


def setup_alarms():
    """Create CloudWatch alarms for critical metrics."""
    cloudwatch = boto3.client("cloudwatch")

    cloudwatch.put_metric_alarm(
        AlarmName="LandTen-High-Error-Rate",
        ComparisonOperator="GreaterThanThreshold",
        EvaluationPeriods=1,
        MetricName="Errors",
        Namespace="LandTen",
        Period=300,
        Statistic="Sum",
        Threshold=10,
        ActionsEnabled=True,
        AlarmDescription="Alert when error rate is high",
    )
    print("✓ Created error rate alarm")


if __name__ == "__main__":
    setup_cloudwatch_logs()
    setup_alarms()
    print("✅ Monitoring setup complete")
