"""
Tempest API integration module.

This module handles all interactions with the Tempest Weather API,
including fetching observations and extracting rainfall data.
"""

import json
import logging
import requests
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# Tempest API base URL
TEMPEST_API_BASE = "https://swd.weatherflow.com/swd/rest"


def get_yesterday_rainfall_data(token, station_id):
    """
    Query Tempest API to get rainfall data from yesterday.
    
    Args:
        token: Tempest API access token
        station_id: Tempest station ID
    
    Returns:
        tuple: (rainfall_observations list, full_api_response dict)
    """
    # Calculate yesterday's date range (UTC)
    now = datetime.now(timezone.utc)
    yesterday_start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_end = yesterday_start + timedelta(days=1)
    
    logger.info(f"Fetching rainfall data from {yesterday_start.isoformat()} to {yesterday_end.isoformat()}")
    
    # Tempest API endpoint for station observations
    url = f"{TEMPEST_API_BASE}/observations/station/{station_id}"
    params = {
        'token': token,
        'time_start': int(yesterday_start.timestamp()),
        'time_end': int(yesterday_end.timestamp())
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"API Response status: {response.status_code}")
        
        # Extract observations - handle different possible response structures
        observations = []
        if isinstance(data, dict):
            observations = data.get('obs', [])
        elif isinstance(data, list):
            observations = data
        
        logger.info(f"Found {len(observations)} observations in API response")
        
        # Filter for observations with rainfall data
        rainfall_observations = []
        for idx, obs in enumerate(observations):
            try:
                # Handle both list and dict formats
                if isinstance(obs, list):
                    # Tempest API returns observations as arrays with specific field positions
                    if len(obs) > 0:
                        rainfall_observations.append({
                            'timestamp': obs[0] if len(obs) > 0 else None,
                            'observation': obs
                        })
                elif isinstance(obs, dict):
                    # Handle dict format if API returns it that way
                    rainfall_observations.append({
                        'timestamp': obs.get('timestamp') or obs.get('time') or obs.get('ts'),
                        'observation': obs
                    })
                else:
                    logger.warning(f"Unexpected observation format at index {idx}: {type(obs)}")
            except (IndexError, KeyError, TypeError) as e:
                logger.warning(f"Error processing observation at index {idx}: {e}")
                continue
        
        return rainfall_observations, data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error querying Tempest API: {str(e)}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing API response: {str(e)}")
        raise


def extract_precip_accum_local_yesterday(api_response):
    """
    Extract precip_accum_local_yesterday from Tempest API response.
    
    The Tempest API may return this value in different places:
    - In the summary data
    - In the latest observation
    - As a separate field in the response
    
    Args:
        api_response: The full API response from Tempest
    
    Returns:
        float: Rainfall amount in mm, or None if not found
    """
    try:
        # Check if response has summary data
        if isinstance(api_response, dict):
            # Check for summary field
            summary = api_response.get('summary', {})
            if summary and 'precip_accum_local_yesterday' in summary:
                value = summary['precip_accum_local_yesterday']
                logger.info(f"Found precip_accum_local_yesterday in summary: {value} mm")
                return value
            
            # Check for obs_summary
            obs_summary = api_response.get('obs_summary', {})
            if obs_summary and 'precip_accum_local_yesterday' in obs_summary:
                value = obs_summary['precip_accum_local_yesterday']
                logger.info(f"Found precip_accum_local_yesterday in obs_summary: {value} mm")
                return value
            
            # Check latest observation
            obs = api_response.get('obs', [])
            if obs and len(obs) > 0:
                # Get the last observation (most recent)
                latest_obs = obs[-1]
                
                # If observation is a dict, check for the field
                if isinstance(latest_obs, dict):
                    if 'precip_accum_local_yesterday' in latest_obs:
                        value = latest_obs['precip_accum_local_yesterday']
                        logger.info(f"Found precip_accum_local_yesterday in latest observation: {value} mm")
                        return value
                
                # If observation is a list, check the field mapping
                # Tempest API field positions vary, but we'll check common positions
                elif isinstance(latest_obs, list) and len(latest_obs) > 0:
                    # Check if there's field mapping info in the response
                    field_map = api_response.get('field_map', {})
                    if field_map:
                        field_index = None
                        for idx, field_name in field_map.items():
                            if field_name == 'precip_accum_local_yesterday':
                                field_index = int(idx)
                                break
                        if field_index is not None and len(latest_obs) > field_index:
                            value = latest_obs[field_index]
                            logger.info(f"Found precip_accum_local_yesterday at index {field_index}: {value} mm")
                            return value
            
            # Check root level
            if 'precip_accum_local_yesterday' in api_response:
                value = api_response['precip_accum_local_yesterday']
                logger.info(f"Found precip_accum_local_yesterday at root level: {value} mm")
                return value
        
        logger.warning("precip_accum_local_yesterday not found in API response")
        logger.debug(f"API response structure: {json.dumps(api_response, indent=2)}")
        return None
        
    except Exception as e:
        logger.error(f"Error extracting precip_accum_local_yesterday: {str(e)}")
        return None
