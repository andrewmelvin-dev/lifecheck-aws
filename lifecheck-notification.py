"""
lifecheck-notification.py

This script is a Lambda function that periodically checks the last verification time 
stored in AWS Systems Manager Parameter Store and sends notification emails if 
certain time thresholds have been exceeded.

It currently implements the following notification logic:
- If more than 30 hours have elapsed since the last verification, an email is sent to the 
  primary contact, including a verification link with a temporary token.
"""

import os
import boto3
import datetime
import secrets
import logging

ssm = boto3.client('ssm')
ses = boto3.client('ses')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

PRIMARY_CONTACT_THRESHOLD_HOURS = 30
SECONDARY_CONTACT_THRESHOLD_HOURS = 40
EMERGENCY_CONTACT_THRESHOLD_HOURS = 48
SECONDS_PER_HOUR = 3600.0
TOKEN_BYTES = 32

def lambda_handler(event, context):

	# Retrieve the environment variables containing parameter names and the email verification URL
	last_verification_param = os.environ.get('LAST_VERIFICATION_PARAM')
	google_account_email_param = os.environ.get('GOOGLE_ACCOUNT_EMAIL_PARAM')
	primary_contact_email_param = os.environ.get('PRIMARY_CONTACT_EMAIL_PARAM')
	primary_contact_message_param = os.environ.get('PRIMARY_CONTACT_MESSAGE_PARAM')
	primary_contact_datetime_param = os.environ.get('PRIMARY_CONTACT_DATETIME_PARAM')
	secondary_contact_email_param = os.environ.get('SECONDARY_CONTACT_EMAIL_PARAM')
	secondary_contact_message_param = os.environ.get('SECONDARY_CONTACT_MESSAGE_PARAM')
	secondary_contact_datetime_param = os.environ.get('SECONDARY_CONTACT_DATETIME_PARAM')
	emergency_contact_email_param = os.environ.get('EMERGENCY_CONTACT_EMAIL_PARAM')
	emergency_contact_message_param = os.environ.get('EMERGENCY_CONTACT_MESSAGE_PARAM')
	emergency_contact_datetime_param = os.environ.get('EMERGENCY_CONTACT_DATETIME_PARAM')
	temp_token_param = os.environ.get('TEMP_TOKEN_PARAM')
	temp_token_generation_time_param = os.environ.get('TEMP_TOKEN_GENERATION_TIME_PARAM')
	email_verification_api_gateway_url = os.environ.get('EMAIL_VERIFICATION_API_GATEWAY_URL')

	# Retrieve parameter values from Parameter Store
	last_verification = None
	try:
		response = ssm.get_parameter(Name=last_verification_param, WithDecryption=False)
		last_verification_str = response['Parameter']['Value']
		if last_verification_str:
			last_verification = datetime.datetime.fromisoformat(last_verification_str)
			logger.info(f"Reading last_verification parameter value of '{last_verification}' from Parameter Store")
	except ssm.exceptions.ParameterNotFound:
		# Default last_verification to current datetime if it has never been set before
		if not last_verification_str:
			last_verification = datetime.datetime.now()
			logger.info(f"The last_verification parameter is not set - setting it now to '{last_verification}'")
			# Store the default value in Parameter Store
			ssm.put_parameter(Name=last_verification_param, Value=last_verification.isoformat(), Type='String', Overwrite=True)

	google_account_email = None
	try:
		response = ssm.get_parameter(Name=google_account_email_param, WithDecryption=False)
		google_account_email = response['Parameter']['Value']
		logger.info(f"Reading google_account_email parameter value of '{google_account_email}' from Parameter Store")
	except ssm.exceptions.ParameterNotFound:
		if not google_account_email:
			logger.error(f"The google_account_email parameter is not set")

	try:
		response = ssm.get_parameters(
			Names=[
				primary_contact_email_param,
				primary_contact_message_param,
				primary_contact_datetime_param,
				secondary_contact_email_param,
				secondary_contact_message_param,
				secondary_contact_datetime_param,
				emergency_contact_email_param,
				emergency_contact_message_param,
				emergency_contact_datetime_param
			],
			WithDecryption=False
		)

		params = {param['Name']: param['Value'] for param in response['Parameters'] if param is not None}

		primary_contact_email = params.get(primary_contact_email_param)
		primary_contact_message = params.get(primary_contact_message_param)
		primary_contact_datetime_str = params.get(primary_contact_datetime_param)
		secondary_contact_email = params.get(secondary_contact_email_param)
		secondary_contact_message = params.get(secondary_contact_message_param)
		secondary_contact_datetime_str = params.get(secondary_contact_datetime_param)
		emergency_contact_email = params.get(emergency_contact_email_param)
		emergency_contact_message = params.get(emergency_contact_message_param)
		emergency_contact_datetime_str = params.get(emergency_contact_datetime_param)

		if not google_account_email or not primary_contact_email or not primary_contact_message or not email_verification_api_gateway_url:
			logger.error(f"Missing required parameters: google_account_email='{google_account_email}' primary_contact_email='{primary_contact_email}' primary_contact_message='{primary_contact_message}' email_verification_api_gateway_url='{email_verification_api_gateway_url}'")
			return {
				"statusCode": 500,
				"body": "Error: Missing required parameters"
			}

		primary_contact_datetime = None
		if primary_contact_datetime_str:
				primary_contact_datetime = datetime.datetime.fromisoformat(primary_contact_datetime_str)

		secondary_contact_datetime = None
		if secondary_contact_datetime_str:
				secondary_contact_datetime = datetime.datetime.fromisoformat(secondary_contact_datetime_str)

		emergency_contact_datetime = None
		if emergency_contact_datetime_str:
				emergency_contact_datetime = datetime.datetime.fromisoformat(emergency_contact_datetime_str)
	except Exception as e:
		logger.error(f"Error retrieving parameters from Parameter Store: {str(e)}")
		return {
			"statusCode": 500,
			"body": f"Error retrieving parameters from Parameter Store: {str(e)}"
		}

	# Check elapsed time and send emails if conditions are met
	current_time = datetime.datetime.now()
	elapsed_hours = (current_time - last_verification).total_seconds() / SECONDS_PER_HOUR

	logger.info(f"Checking elapsed time: current_time='{current_time}' elapsed_hours='{elapsed_hours}'")
	if elapsed_hours > PRIMARY_CONTACT_THRESHOLD_HOURS and elapsed_hours <= SECONDARY_CONTACT_THRESHOLD_HOURS:
		logger.info(f"Checking last primary contact time: primary_contact_datetime='{primary_contact_datetime}'")
		# Check if primary contact email has already been sent within the last hour
		if not primary_contact_datetime or current_time - primary_contact_datetime > datetime.timedelta(hours=1):
			logger.info(f"Attempting to send message to the primary contact...")
			# Generate a temporary token and store it in Parameter Store
			temp_token = secrets.token_urlsafe(TOKEN_BYTES)
			temp_token_generation_time = current_time.isoformat()

			ssm.put_parameter(Name=temp_token_param, Value=temp_token, Type='String', Overwrite=True)
			ssm.put_parameter(Name=temp_token_generation_time_param, Value=temp_token_generation_time, Type='String', Overwrite=True)
			logger.info(f"Temporary verification token has been generated")

			# Construct the verification URL
			verification_url = f"{email_verification_api_gateway_url}?token={temp_token}"

			# Include the verification URL in the email message
			email_body_with_url = f"{primary_contact_message}\n\nVerification URL: {verification_url}"

			# Send the primary contact email
			try:
				# First confirm that the destination email address is verified in SES
				verified_identities = ses.list_verified_email_addresses()['VerifiedEmailAddresses']
				if primary_contact_email not in verified_identities:
					logger.error(f"Error sending email: Destination email address {primary_contact_email} is not verified in SES")
					return {
						"statusCode": 500,
						"body": f"Error: Destination email address {primary_contact_email} is not verified in SES"
					}

				ses.send_email(
					Source=google_account_email,
					Destination={'ToAddresses': [primary_contact_email]},
					Message={
						'Subject': {'Data': 'Lifecheck Verification Timeout'},
						'Body': {'Text': {'Data': email_body_with_url}}
					}
				)

				# Update the time the primary contact was last contacted
				ssm.put_parameter(Name=primary_contact_datetime_param, Value=current_time.isoformat(), Type='String', Overwrite=True)

				logger.info(f"Primary contact email sent successfully to '{primary_contact_email}'")
				return {
					"statusCode": 200,
					"body": "Primary contact email sent successfully"
				}

			except Exception as e:
				logger.error(f"Error sending email: {str(e)}")
				return {
					"statusCode": 500,
					"body": f"Error sending email: {str(e)}"
				}
	elif elapsed_hours > SECONDARY_CONTACT_THRESHOLD_HOURS and elapsed_hours <= EMERGENCY_CONTACT_THRESHOLD_HOURS:
		logger.info(f"Checking last secondary contact time: secondary_contact_datetime='{secondary_contact_datetime}'")
		# Check if secondary contact email has already been sent
		if not secondary_contact_datetime:
			logger.info(f"Attempting to send message to the secondary contact...")

			# Send the secondary contact email
			try:
				# First confirm that the destination email address is verified in SES
				verified_identities = ses.list_verified_email_addresses()['VerifiedEmailAddresses']
				if secondary_contact_email not in verified_identities:
					logger.error(f"Error sending email: Destination email address {secondary_contact_email} is not verified in SES")
					return {
						"statusCode": 500,
						"body": f"Error: Destination email address {secondary_contact_email} is not verified in SES"
					}

				ses.send_email(
					Source=google_account_email,
					Destination={'ToAddresses': [secondary_contact_email]},
					Message={
						'Subject': {'Data': 'Warning: Lifecheck Verification Timeout'},
						'Body': {'Text': {'Data': secondary_contact_message}}
					}
				)

				# Update the time the secondary contact was last contacted
				ssm.put_parameter(Name=secondary_contact_datetime_param, Value=current_time.isoformat(), Type='String', Overwrite=True)

				logger.info(f"Secondary contact email sent successfully to '{secondary_contact_email}'")
				return {
					"statusCode": 200,
					"body": "Secondary contact email sent successfully"
				}

			except Exception as e:
				logger.error(f"Error sending email: {str(e)}")
				return {
					"statusCode": 500,
					"body": f"Error sending email: {str(e)}"
				}
	elif elapsed_hours > EMERGENCY_CONTACT_THRESHOLD_HOURS:
		logger.info(f"Checking last emergency contact time: emergency_contact_datetime='{emergency_contact_datetime}'")
		# Check if emergency contact notifications have already been sent
		if not emergency_contact_datetime:
			logger.info(f"Attempting to send message to the emergency contact...")

			# Send the emergency contact email
			try:
				# First confirm that the destination email address is verified in SES
				verified_identities = ses.list_verified_email_addresses()['VerifiedEmailAddresses']
				if emergency_contact_email not in verified_identities:
					logger.error(f"Error sending email: Destination email address {emergency_contact_email} is not verified in SES")
					return {
						"statusCode": 500,
						"body": f"Error: Destination email address {emergency_contact_email} is not verified in SES"
					}

				ses.send_email(
					Source=google_account_email,
					Destination={'ToAddresses': [emergency_contact_email]},
					Message={
						'Subject': {'Data': 'Emergency: Lifecheck Verification Timeout'},
						'Body': {'Text': {'Data': emergency_contact_message}}
					}
				)

				# Update the time the emergency contact was last contacted
				ssm.put_parameter(Name=emergency_contact_datetime_param, Value=current_time.isoformat(), Type='String', Overwrite=True)

				logger.info(f"Emergency contact email sent successfully to '{emergency_contact_email}'")
				return {
					"statusCode": 200,
					"body": "Emergency contact email sent successfully"
				}

			except Exception as e:
				logger.error(f"Error sending email: {str(e)}")
				return {
					"statusCode": 500,
					"body": f"Error sending email: {str(e)}"
				}		
	logger.info(f"No action needed at this time")
	return {
		"statusCode": 200,
		"body": "No action needed at this time"
	}
