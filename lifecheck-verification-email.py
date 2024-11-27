"""
lifecheck-verification-email.py

This script is a Lambda function that handles email verification requests. 

It performs the following tasks:

1. Retrieves a temporary token from the query string parameter of the request.
2. Fetches the stored token and its generation time from AWS Systems Manager Parameter Store.
3. Verifies if the provided token matches the stored token and if it's still valid (not expired).
4. If the token is valid and not expired:
    - Updates the `last_verification` parameter in Parameter Store with the current datetime.
    - Clears other relevant datetime parameters (e.g., notification timestamps).
5. Returns an appropriate success or error response based on the verification outcome.

This function is typically triggered by an API Gateway endpoint that is accessed via a verification link 
sent in an email. 
"""

import os
import boto3
import datetime
import logging

ssm = boto3.client('ssm')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

TOKEN_VALID_DURATION = 2

def lambda_handler(event, context):

	# Retrieve the environment variables containing parameter names
	last_verification_param = os.environ.get('LAST_VERIFICATION_PARAM')
	primary_contact_datetime_param = os.environ.get('PRIMARY_CONTACT_DATETIME_PARAM')
	secondary_contact_datetime_param = os.environ.get('SECONDARY_CONTACT_DATETIME_PARAM')
	emergency_contact_datetime_param = os.environ.get('EMERGENCY_CONTACT_DATETIME_PARAM')
	temp_token_param = os.environ.get('TEMP_TOKEN_PARAM')
	temp_token_generation_time_param = os.environ.get('TEMP_TOKEN_GENERATION_TIME_PARAM')

	# Retrieve the token from the URL query string parameter
	provided_token = event['queryStringParameters']['token']

	# Retrieve the stored token and its generation time from Parameter Store
	try:
		response = ssm.get_parameters(
			Names=[temp_token_param, temp_token_generation_time_param],
			WithDecryption=False
		)

		stored_token = None
		stored_token_generation_time_str = None

		for param in response['Parameters']:
			if param['Name'] == temp_token_param:
				stored_token = param['Value']
			elif param['Name'] == temp_token_generation_time_param:
				stored_token_generation_time_str = param['Value']

		if not stored_token or not stored_token_generation_time_str:
			logger.error(f"Missing required parameters: stored_token='{stored_token}' stored_token_generation_time_str='{stored_token_generation_time_str}'")
			return {
				"statusCode": 500,
				"body": "Error retrieving stored token or generation time"
			}

		stored_token_generation_time = datetime.datetime.fromisoformat(stored_token_generation_time_str)

	except Exception as e:
		logger.error(f"Error retrieving token from Parameter Store: {str(e)}")
		return {
			"statusCode": 500,
			"body": f"Error retrieving token from Parameter Store: {str(e)}"
		}

	# Verify the token and its validity 
	current_time = datetime.datetime.now()
	token_valid_duration = datetime.timedelta(hours=TOKEN_VALID_DURATION)

	logger.info(f"Checking tokens and elapsed time: provided_token='{provided_token}' stored_token='{stored_token}' current_time='{current_time}' stored_token_generation_time='{stored_token_generation_time}'")
	if provided_token != stored_token:
		logger.error(f"The provided token is invalid")
		return {
			"statusCode": 401,
			"body": "Invalid token"
		}
	elif current_time - stored_token_generation_time > token_valid_duration:
		logger.error(f"The provided token has expired")
		return {
			"statusCode": 401,
			"body": "Token has expired"
		}

	# If the token is valid then update last_verification and clear the other notification parameters
	ssm.put_parameter(Name=last_verification_param, Value=current_time.isoformat(), Type='String', Overwrite=True)

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

	# Define the HTML content to return as a response
	html_content = f"""
	<!DOCTYPE html>
		<head>
			<meta charset="UTF-8">
			<meta name="viewport" content="width=device-width, initial-scale=1">
			<title>Lifecheck Settings</title>
			<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bulma@1.0.2/css/bulma.min.css">
		</head>
		<body>
			<section class="section">
				<div class="container">
					<h1 class="title is-spaced">Lifecheck Email Verification</h1>
					<section class="hero is-success mt-2">
						<div class="hero-body">
							<p class="title is-spaced has-text-white">Thank you!</p>
							<p class="subtitle has-text-white">Your verification has been successful.</p>
						</div>
					</section>
				</div>
			</section>
		</body>
	</html>
	"""

	# Return the HTML content and a successful status code
	return {
		"statusCode": 200,
		"headers": { "Content-Type": "text/html" },
		"body": html_content
	}
