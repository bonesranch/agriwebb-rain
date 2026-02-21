"""
AgriWebb API integration module.

This module handles all interactions with the AgriWebb GraphQL API,
including updating rainfall records.
"""

import json
import logging
import requests

logger = logging.getLogger(__name__)

# AgriWebb API base URL
AGRIWEBB_API_BASE = "https://api.agriwebb.com/v2"
# Assumed rainfall gauge, change if your rainfall gauge is not this name
RAIN_GAUGE_NAME = "Tempest"
RAIN_GAUGE_UNIT = "inch"
RAIN_GAUGE_MODE = "cumulative"


def log_enum_values(access_token, enum_name):
    """
    Log the enum values for a given enum name.
    
    Args:
        access_token: AgriWebb OAuth access token
        enum_name: AgriWebb enum name
    Raises:
        requests.exceptions.RequestException: If the request to AgriWebb fails
        Exception: If the request to AgriWebb fails
    """
    logger.info(f"Logging enum values for: {enum_name}")
    query = """
    {
      __type(name: "%s") {
        enumValues {
          name
        }
      }
    }
    """ % enum_name
    headers = {
        "x-api-key": f"{access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "query": query
    }
    try:
      response = requests.post(
          AGRIWEBB_API_BASE,
          headers=headers,
          json=payload,
          timeout=30
      )
      response.raise_for_status()
      result = response.json()
      logger.info(f"Enum values for {enum_name}: {json.dumps(result, indent=2)}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error logging enum values: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response: {json.dumps(e.response.json(), indent=2)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error logging enum values: {str(e)}")
        raise


def get_rain_gauge_sensor_id(access_token, farm_id):
    """
    Get the sensor ID for a rain gauge from AgriWebb.
    
    Args:
        access_token: AgriWebb OAuth access token
        farm_id: AgriWebb farm ID
    """
    query = """
    {
      mapFeatures(filter: {
        type: { _eq: RAIN_GAUGE }
        farmId: { _eq: "%s" }
      }) {
        id
        name
        type
        farmId
      }
    }
    """ % farm_id
    headers = {
        "x-api-key": f"{access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "query": query
    }
    try:
      response = requests.post(
          AGRIWEBB_API_BASE,
          headers=headers,
          json=payload,
          timeout=30
      )
      response.raise_for_status()
      result = response.json()
      if result['data']['mapFeatures'] is not None and len(result['data']['mapFeatures']) > 0:
        return result['data']['mapFeatures'][0]['id']
      else:
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting rain gauge sensor ID: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response: {json.dumps(e.response.json(), indent=2)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting rain gauge sensor ID: {str(e)}")
        raise


def update_rainfall(access_token, farm_id, rainfall_inches, time_ms):
    """
    Update AgriWebb with rainfall data using the addRainfalls GraphQL mutation.
    
    See: https://docs.agriwebb.com/graphql/inputs/add-rainfall-input
    
    Args:
        access_token: AgriWebb OAuth access token
        farm_id: AgriWebb farm ID
        rainfall_inches: Rainfall amount in inches
        time_ms: UNIX epoch timestamp in milliseconds (when rainfall was recorded)
    
    Returns:
        dict: GraphQL response
    """

    logger.info(f"Getting rain gauge sensor ID for farm: {farm_id}")
    sensor_id = get_rain_gauge_sensor_id(access_token, farm_id)
    if sensor_id is None:
        logger.info(f"Rain gauge sensor ID not found for name: {RAIN_GAUGE_NAME}, creating a new rain gauge")
        create_rain_gauge(access_token, farm_id)
        logger.info(f"Rain gauge created, getting sensor ID again")
        sensor_id = get_rain_gauge_sensor_id(access_token, farm_id)
        if sensor_id is None:
            logger.error(f"Rain gauge sensor ID not found for name: {RAIN_GAUGE_NAME}")
            raise ValueError(f"Rain gauge sensor ID not found for name: {RAIN_GAUGE_NAME}")
    
    mutation = """
    mutation {
      addRainfalls(input: {
        farmId: "%s"
        sensorId: "%s"
        value: %.2f
        unit: %s
        mode: %s
        time: %d
      }) {
        rainfalls {
          time
          mode
        }
      }
    }
    """ % (farm_id, sensor_id, rainfall_inches, RAIN_GAUGE_UNIT, RAIN_GAUGE_MODE, time_ms)
    
    headers = {
        "x-api-key": f"{access_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "query": mutation
    }
    
    try:
        logger.info(f"Updating AgriWebb with rainfall: {rainfall_inches} inches")
        response = requests.post(
            AGRIWEBB_API_BASE,
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        
        # Check for GraphQL errors
        if 'errors' in result:
            error_messages = [err.get('message', str(err)) for err in result['errors']]
            raise ValueError(f"GraphQL errors: {', '.join(error_messages)}")
        
        logger.info(f"Successfully updated AgriWebb rainfall record")
        logger.debug(f"AgriWebb response: {json.dumps(result, indent=2)}")
        return result
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error updating AgriWebb: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response: {json.dumps(e.response.json(), indent=2)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error updating AgriWebb: {str(e)}")
        raise
