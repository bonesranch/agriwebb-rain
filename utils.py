"""
Utility functions for AWS Lambda function.

This module contains shared utility functions used across the application,
such as SSM Parameter Store access.
"""

import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def get_parameter_from_ssm(parameter_name):
    """
    Generic function to retrieve a parameter from AWS SSM Parameter Store.
    
    Args:
        parameter_name: Name of the SSM parameter
    
    Returns:
        str: Parameter value
    
    Raises:
        ValueError: If the parameter cannot be retrieved
    """
    try:
        ssm_client = boto3.client('ssm')
        response = ssm_client.get_parameter(
            Name=parameter_name,
            WithDecryption=True  # Required for SecureString parameters
        )
        if 'Parameter' not in response or 'Value' not in response['Parameter']:
            raise ValueError(f"Unexpected SSM response structure for parameter '{parameter_name}'")
        
        value = response['Parameter']['Value']
        logger.info(f"Successfully retrieved parameter '{parameter_name}' from SSM Parameter Store")
        return value
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ParameterNotFound':
            raise ValueError(f"SSM parameter '{parameter_name}' not found")
        elif error_code == 'AccessDeniedException':
            raise ValueError(f"Access denied to SSM parameter '{parameter_name}'. Check IAM permissions.")
        else:
            raise ValueError(f"Error retrieving SSM parameter '{parameter_name}': {str(e)}")
    except Exception as e:
        raise ValueError(f"Unexpected error retrieving SSM parameter '{parameter_name}': {str(e)}")
