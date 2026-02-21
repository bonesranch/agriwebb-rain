# Agriwebb Rain

A scheduled AWS Lambda function (cron job) that automates the update of rain data from Tempest (local weather station) into Agriwebb.

## Structure

- `main.py` - Main Lambda handler function (orchestrates the workflow)
- `tempest.py` - Tempest API integration module
- `agriwebb.py` - AgriWebb API integration module
- `utils.py` - Shared utility functions (SSM Parameter Store access)
- `requirements.txt` - Python dependencies
- `test_local.py` - Local testing script
- `serverless.yml` - Serverless Framework configuration

## Prerequisites

- Python 3.11+
- Node.js and npm (for Serverless Framework)
- AWS CLI configured with credentials

## Setup

1. Install Serverless Framework globally:
```bash
npm install -g serverless
```

2. Install Serverless Python Requirements plugin:
```bash
npm install --save-dev serverless-python-requirements
```

3. Install Python dependencies:
```bash
pip3 install -r requirements.txt
```

4. Set up Tempest API credentials in AWS SSM Parameter Store:
   - Sign in to [Tempest Web App](https://tempestwx.com)
   - Go to Settings -> Data Authorizations -> Create Token
   - Copy your Personal Access Token
   - Store the token in AWS SSM Parameter Store as a SecureString:
   ```bash
   # Store Tempest API token
   aws ssm put-parameter \
     --name "bonesranch.agriwebb-rain.tempest.token" \
     --value "your_token_here" \
     --type "SecureString" \
     --description "Tempest API access token for agriwebb-rain Lambda"
   
   # Store Tempest station ID
   aws ssm put-parameter \
     --name "bonesranch.agriwebb-rain.tempest.station_id" \
     --value "your_token_here" \
     --type "SecureString" \
     --description "Tempest station ID for agriwebb-rain Lambda"
   ```

5. Set up AgriWebb API credentials in AWS SSM Parameter Store:
   - Obtain an API access token from AgriWebb (requires contacting support)
   - Get your Farm ID from AgriWebb (in the URL after you login, https://portal.agriwebb.com/f/{farm_id}/dashboard)
   - Create a rain gauge in AgriWebb (We used the API to create this)
   ```bash
   # Store AgriWebb access token
   aws ssm put-parameter \
     --name "bonesranch.agriwebb-rain.agriwebb.access_token" \
     --value "your_access_token_here" \
     --type "SecureString" \
     --description "AgriWebb API access token for agriwebb-rain Lambda"
   
   # Store AgriWebb Farm ID
   aws ssm put-parameter \
     --name "bonesranch.agriwebb-rain.agriwebb.farm_id" \
     --value "your_farm_id_here" \
     --type "SecureString" \
     --description "AgriWebb Farm ID for agriwebb-rain Lambda"
   
   # Optional: Store rain gauge name to match (if you have multiple rain gauges)
   # If not set, the first rain gauge for the farm will be used
   aws ssm put-parameter \
     --name "bonesranch.agriwebb-rain.agriwebb.rain_gauge_name" \
     --value "Tempest" \
     --type "SecureString" \
     --description "AgriWebb rain gauge name to match (case-insensitive)"
   ```

## Deployment

### Using Serverless Framework (Recommended)

Environment Variables:
Serverless expects an environment variable `ALARM_EMAIL` for setting up the SNS topic for alerting
```bash
export ALARM_EMAIL=your@email.com
```

1. Deploy to dev stage (default):
```bash
serverless deploy
```

2. Deploy to a specific stage:
```bash
serverless deploy --stage prod
```

3. Deploy to a specific region:
```bash
serverless deploy --region us-west-2
```

4. Deploy only the function (faster):
```bash
serverless deploy function -f rain
```

5. View deployment info:
```bash
serverless info
```

6. Remove all resources:
```bash
serverless remove
```

## Local Testing

**Prerequisites:** 
- The SSM parameters must exist in AWS (created during setup)
- AWS credentials configured with access to the SSM parameter

### Option 1: Use AWS Credentials (Recommended)

Make sure your AWS credentials are configured and have access to the SSM parameter:
```bash
aws configure
```

Then run the test script:
```bash
python3 test_local.py
```

The test script will:
- Retrieve the Tempest token from SSM Parameter Store
- Query the Tempest API for yesterday's rainfall data
- Log all observations found
- Display the results
- Update Agriwebb with yesterdays rainfall

### Option 2: Temporary Environment Variable for Local Testing

### Schedule Configuration

The function is configured to run daily at 2:00 AM UTC. You can modify the schedule in `serverless.yml`:

```yaml
events:
  - schedule:
      rate: cron(0 2 * * ? *)  # Daily at 2 AM UTC
      enabled: true
```

Common cron expressions:
- `cron(0 2 * * ? *)` - Daily at 2:00 AM UTC
- `cron(0 */6 * * ? *)` - Every 6 hours
- `cron(0 0 * * ? *)` - Daily at midnight UTC
- `rate(5 minutes)` - Every 5 minutes (for testing)

## Configuration

### Environment Variables

**Configuration:**

- **Tempest Token**: Stored in AWS SSM Parameter Store at `bonesranch.agriwebb-rain.tempest.token`
- **Station ID**: Stored in AWS SSM Parameter Store at `bonesranch.agriwebb-rain.tempest.station_id`
- **AgriWebb Access Token**: Stored in AWS SSM Parameter Store at `bonesranch.agriwebb-rain.agriwebb.access_token`
- **AgriWebb Farm ID**: Stored in AWS SSM Parameter Store at `bonesranch.agriwebb-rain.agriwebb.farm_id`
- **AgriWebb Rain Gauge Name** (optional): Stored in AWS SSM Parameter Store at `bonesranch.agriwebb-rain.agriwebb.rain_gauge_name`. If set, the function matches the rain gauge by name (case-insensitive). If not set, the first rain gauge for the farm is used. The function queries `mapFeatures` for RAIN_GAUGE type to find the sensor.

The Lambda function uses the [addRainfalls](https://docs.agriwebb.com/graphql/inputs/add-rainfall-input) mutation, fetches rain gauges from AgriWebb at runtime to find the sensor ID, and retrieves credentials from SSM Parameter Store. Make sure all required parameters exist before deploying.
- The function extracts `precip_accum_local_yesterday` from the Tempest API response. If this field is not available in the expected location, the function will log a warning and skip the AgriWebb update.

The IAM role is automatically configured with permissions to read from SSM Parameter Store. No environment variables are needed for deployment.

### IAM Permissions

Add IAM role statements in `serverless.yml` under `provider.iam.role.statements`:

```yaml
provider:
  iam:
    role:
      statements:
        - Effect: Allow
          Action:
            - s3:GetObject
          Resource: arn:aws:s3:::your-bucket/*
```

## Monitoring

View CloudWatch logs:
```bash
serverless logs -f rain --tail
```

View function info:
```bash
serverless info
```

Invoke function manually (for testing):
```bash
serverless invoke -f rain
```

## Development Workflow

1. **Initial Setup:**
   - Create SSM parameters for Tempest and Agriwebb(see Setup section)
   - Deploy function: `serverless deploy`

2. **Development Cycle:**
   - Make changes to `main.py`
   - Test locally: `python test_local.py` (requires SSM parameter to exist)
   - Deploy: `serverless deploy`
   - Monitor logs: `serverless logs -f rain --tail`
   - Test manually: `serverless invoke -f rain`
