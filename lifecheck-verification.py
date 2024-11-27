"""
lifecheck-verification.py

This script is a Lambda function that handles token verification requests. 

It performs the following tasks:

1. Updates the `last_verification` parameter in Parameter Store with the current datetime.
2. Clears other relevant datetime parameters (e.g., notification timestamps).
3. Returns a success response.

This function is typically triggered by an API Gateway endpoint that receives verification
requests from external clients or services, which is secured using an API key that was generated
during the deployment process.
"""

import os
import boto3
import datetime
import logging

ssm = boto3.client('ssm')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):

	logger.info(f"Attempting to perform verification...")

	# Retrieve the environment variables containing parameter names
	last_verification_param = os.environ.get('LAST_VERIFICATION_PARAM')
	primary_contact_datetime_param = os.environ.get('PRIMARY_CONTACT_DATETIME_PARAM')
	secondary_contact_datetime_param = os.environ.get('SECONDARY_CONTACT_DATETIME_PARAM')
	emergency_contact_datetime_param = os.environ.get('EMERGENCY_CONTACT_DATETIME_PARAM')
	temp_token_param = os.environ.get('TEMP_TOKEN_PARAM')
	temp_token_generation_time_param = os.environ.get('TEMP_TOKEN_GENERATION_TIME_PARAM')
    
	# Update last_verification and clear the other notification parameters
	current_datetime = datetime.datetime.now().isoformat()
	logger.info(f"Setting last_verification='{current_datetime}'")
	ssm.put_parameter(Name=last_verification_param, Value=current_datetime, Type='String', Overwrite=True)

	logger.info(f"Clearing previous notification datetimes...")
	parameters_to_clear = [
		primary_contact_datetime_param,
		secondary_contact_datetime_param,
		emergency_contact_datetime_param,
		temp_token_param,
		temp_token_generation_time_param
	]

	try:
		for param in parameters_to_clear:
			ssm.delete_parameter(Name=param)
	except Exception as e:
		logger.error(f"Error deleting parameter from Parameter Store: {str(e)}")

	logger.info(f"Verification has been successful")
	return {
		"statusCode": 200,
		"body": "Verification successful and parameters updated"
	}
