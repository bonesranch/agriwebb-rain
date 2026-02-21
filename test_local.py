#!/usr/bin/env python3
"""
Local test script for cron Lambda function.
Run with: python test_local.py

PREREQUISITE: AWS credentials to be able to query SSM parameters
"""

import json
import os
import logging
import sys
from datetime import datetime
from main import lambda_handler

# Configure logging to show in console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)


class MockContext:
    """Mock Lambda context object for local testing."""
    
    def __init__(self):
        self.function_name = "agriwebb-rain-rain"
        self.function_version = "$LATEST"
        self.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:agriwebb-rain-rain"
        self.memory_limit_in_mb = 128
        self.aws_request_id = "test-request-id"
        self.log_group_name = "/aws/lambda/agriwebb-rain-rain"
        self.log_stream_name = "2024/01/01/[$LATEST]test-stream"
        self.remaining_time_in_millis = lambda: 30000


def test_eventbridge_event():
    """Test with a standard EventBridge/CloudWatch Events event."""
    print("=" * 60)
    print("Test 1: EventBridge Scheduled Event")
    print("=" * 60)
    
    event = {
        'version': '0',
        'id': 'test-event-id',
        'detail-type': 'Scheduled Event',
        'source': 'aws.events',
        'account': '123456789012',
        'time': datetime.utcnow().isoformat() + 'Z',
        'region': 'us-east-1',
        'resources': [
            'arn:aws:events:us-east-1:123456789012:rule/test-rule'
        ],
        'detail': {}
    }
    
    context = MockContext()
    try:
        result = lambda_handler(event, context)
        print(f"\n✅ Test passed!")
        print(f"Result: {json.dumps(result, indent=2)}")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    print()


def run_all_tests():
    """Run all test cases."""
    print("\n" + "=" * 60)
    print("Running Local Cron Lambda Function Tests")
    print("=" * 60 + "\n")
    
    try:
        test_eventbridge_event()
        
        print("=" * 60)
        print("All tests completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
