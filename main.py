"""
AWS Lambda function handler for agriwebb-rain.

This function orchestrates the process of:
1. Retrieving rainfall data from Tempest API
2. Extracting yesterday's rainfall amount
3. Updating AgriWebb with the rainfall data
"""

import json
import logging
from datetime import datetime, timedelta, timezone

from tempest import (
    get_yesterday_rainfall_data,
    extract_precip_accum_local_yesterday
)
from agriwebb import update_rainfall
from utils import get_parameter_from_ssm

# SSM Parameter Store paths
TEMPEST_TOKEN_PARAMETER = "bonesranch.agriwebb-rain.tempest.token"
TEMPEST_STATION_ID_PARAMETER = "bonesranch.agriwebb-rain.tempest.station_id"
AGRIWEBB_ACCESS_TOKEN_PARAMETER = "bonesranch.agriwebb-rain.agriwebb.access_token"
AGRIWEBB_FARM_ID_PARAMETER = "bonesranch.agriwebb-rain.agriwebb.farm_id"

# Conversion: Tempest returns metric (mm), we put inches into AgriWebb
MM_TO_INCHES = 1 / 25.4

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Add console handler if not already present (for local testing)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def lambda_handler(event, context):
    """
    AWS Lambda function handler for scheduled/cron execution.
    
    Args:
        event: The event dict from EventBridge/CloudWatch Events
        context: The Lambda context object
    
    Returns:
        dict: Result of the execution
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Extract schedule information
        event_time = event.get('time', 'N/A')
        event_source = event.get('source', 'N/A')
        
        logger.info(f"Event triggered at {event_time} from {event_source}")
        
        # Get Tempest token from SSM Parameter Store
        logger.info(f"Retrieving Tempest token from SSM Parameter Store: {TEMPEST_TOKEN_PARAMETER}")
        tempest_token = get_parameter_from_ssm(TEMPEST_TOKEN_PARAMETER)

        # Get Tempest station id from SSM Parameter Store
        logger.info(f"Retrieving Tempest station id from SSM Parameter Store: {TEMPEST_STATION_ID_PARAMETER}")
        tempest_station_id = get_parameter_from_ssm(TEMPEST_STATION_ID_PARAMETER)
        
        logger.info(f"Querying Tempest API for yesterday's rainfall data (Station ID: {tempest_station_id})...")
        
        # Query Tempest API for yesterday's rainfall data
        rainfall_observations, api_response = get_yesterday_rainfall_data(
            tempest_token, 
            tempest_station_id
        )
        
        # Log the rainfall data
        logger.info("=" * 60)
        logger.info("YESTERDAY'S RAINFALL DATA")
        logger.info("=" * 60)
        logger.info(f"Total observations found: {len(rainfall_observations)}")
        
        # Extract precip_accum_local_yesterday
        rainfall_mm = extract_precip_accum_local_yesterday(api_response)
        
        if rainfall_mm is not None:
            logger.info(f"Extracted precip_accum_local_yesterday: {rainfall_mm} mm")
            
            # Convert from metric (mm) to inches for AgriWebb
            rainfall_inches = round(rainfall_mm * MM_TO_INCHES, 3)
            logger.info(f"Converted to {rainfall_inches} inches for AgriWebb")
            
            # Get yesterday's date and timestamp (midnight UTC)
            yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date()
            date_str = yesterday.isoformat()
            # AgriWebb expects UNIX epoch time in milliseconds
            yesterday_midnight = datetime(yesterday.year, yesterday.month, yesterday.day, tzinfo=timezone.utc)
            time_ms = int(yesterday_midnight.timestamp() * 1000)
            
            # Get AgriWebb credentials from SSM
            logger.info("Retrieving AgriWebb credentials from SSM Parameter Store...")
            agriwebb_access_token = get_parameter_from_ssm(AGRIWEBB_ACCESS_TOKEN_PARAMETER)
            agriwebb_farm_id = get_parameter_from_ssm(AGRIWEBB_FARM_ID_PARAMETER)
            
            # Update AgriWebb with rainfall data (in inches)
            logger.info(f"Updating AgriWebb with {rainfall_inches} inches rainfall for {date_str}...")
            agriwebb_result = update_rainfall(
                agriwebb_access_token,
                agriwebb_farm_id,
                rainfall_inches,
                time_ms
            )
            
            logger.info("=" * 60)
            logger.info("AGRIWEBB UPDATE RESULT")
            logger.info("=" * 60)
            logger.info(f"Successfully updated AgriWebb: {json.dumps(agriwebb_result, indent=2)}")
            
            result = {
                'status': 'success',
                'message': 'Successfully retrieved and updated rainfall data',
                'event_time': event_time,
                'rainfall_mm': rainfall_mm,
                'rainfall_inches': rainfall_inches,
                'date': date_str,
                'observations_count': len(rainfall_observations),
                'agriwebb_updated': True
            }
        else:
            logger.warning("Could not extract precip_accum_local_yesterday from Tempest API response")
            logger.info("Skipping AgriWebb update - no rainfall data available")
            
            result = {
                'status': 'partial_success',
                'message': 'Retrieved observations but could not extract rainfall amount',
                'event_time': event_time,
                'observations_count': len(rainfall_observations),
                'rainfall_mm': None,
                'agriwebb_updated': False
            }
        
        logger.info("=" * 60)
        logger.info(f"Task completed: {result['status']}")
        return result
    except Exception as e:
        logger.error(f"Error executing cron job: {str(e)}", exc_info=True)
        # Re-raise to mark the invocation as failed
        raise
