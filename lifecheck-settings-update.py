"""
lifecheck-settings-update.py

This script is a Lambda function updates the values provided in the HTML form
that was rendered in the lifecheck-settings-view.py script.
"""

import os
import boto3
import logging
import urllib.parse

ssm = boto3.client('ssm')
ses = boto3.client('sesv2', region_name=os.environ.get('REGION'))
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def save_and_verify_email(key_param, new_value):
	try:
		response = ssm.get_parameter(
			Name=key_param,
			WithDecryption=False
		)
		current_key_value = response['Parameter']['Value']
	except ssm.exceptions.ParameterNotFound:
		current_key_value = None

	# Check whether the key value has changed
	if current_key_value != new_value:
		# Save the new value
		ssm.put_parameter(
			Name=key_param,
			Value=new_value,
			Type='String',
			Overwrite=True
		)
		# Verify the new email address via SES
		response = ses.create_email_identity(
			EmailIdentity=new_value
		)

def save_parameter(key_param, new_value):
	try:
		response = ssm.get_parameter(
			Name=key_param,
			WithDecryption=False
		)
		current_key_value = response['Parameter']['Value']
	except ssm.exceptions.ParameterNotFound:
		current_key_value = None

	# Check whether the key value has changed
	if current_key_value != new_value:
		# Save the new value
		ssm.put_parameter(
			Name=key_param,
			Value=new_value,
			Type='String',
			Overwrite=True
		)

def lambda_handler(event, context):

	html_header = f"""
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
						<h1 class="title is-spaced">Lifecheck Settings</h1>
	"""
	html_footer = f"""
					</div>
				</section>
			</body>
		</html>
	"""

	try:
		logger.info(f"Attempting to update settings")

		# Retrieve the environment variables containing parameter names
		primary_contact_email_param = os.environ.get('PRIMARY_CONTACT_EMAIL_PARAM')
		primary_contact_message_param = os.environ.get('PRIMARY_CONTACT_MESSAGE_PARAM')
		secondary_contact_email_param = os.environ.get('SECONDARY_CONTACT_EMAIL_PARAM')
		secondary_contact_message_param = os.environ.get('SECONDARY_CONTACT_MESSAGE_PARAM')
		emergency_contact_email_param = os.environ.get('EMERGENCY_CONTACT_EMAIL_PARAM')
		emergency_contact_phone_param = os.environ.get('EMERGENCY_CONTACT_PHONE_PARAM')
		emergency_contact_message_param = os.environ.get('EMERGENCY_CONTACT_MESSAGE_PARAM')

		# Get the raw request body
		body = event.get("body", "")
		
		logger.info(f"Parsing updated values")

		# Parse the URL-encoded form data
		form_data = urllib.parse.parse_qs(body)
		
		# Extract form fields and update the values in Parameter Store
		primary_contact_email = form_data.get("primary_contact_email", [None])[0]
		if primary_contact_email:
			logger.info(f"Retrieved value from form: primary_contact_email='{primary_contact_email}'")
			save_and_verify_email(primary_contact_email_param, primary_contact_email)

		primary_contact_message = form_data.get("primary_contact_message", [None])[0]
		if primary_contact_message:
			logger.info(f"Retrieved value from form: primary_contact_message='{primary_contact_message}'")
			save_parameter(primary_contact_message_param, primary_contact_message)

		secondary_contact_email = form_data.get("secondary_contact_email", [None])[0]
		if secondary_contact_email:
			logger.info(f"Retrieved value from form: secondary_contact_email='{secondary_contact_email}'")
			save_and_verify_email(secondary_contact_email_param, secondary_contact_email)

		secondary_contact_message = form_data.get("secondary_contact_message", [None])[0]
		if secondary_contact_message:
			logger.info(f"Retrieved value from form: secondary_contact_message='{secondary_contact_message}'")
			save_parameter(secondary_contact_message_param, secondary_contact_message)

		emergency_contact_email = form_data.get("emergency_contact_email", [None])[0]
		if emergency_contact_email:
			logger.info(f"Retrieved value from form: emergency_contact_email='{emergency_contact_email}'")
			save_and_verify_email(emergency_contact_email_param, emergency_contact_email)

		emergency_contact_phone = form_data.get("emergency_contact_phone", [None])[0]
		if emergency_contact_phone:
			logger.info(f"Retrieved value from form: emergency_contact_phone='{emergency_contact_phone}'")
			save_parameter(emergency_contact_phone_param, emergency_contact_phone)

		emergency_contact_message = form_data.get("emergency_contact_message", [None])[0]
		if emergency_contact_message:
			logger.info(f"Retrieved value from form: emergency_contact_message='{emergency_contact_message}'")
			save_parameter(emergency_contact_message_param, emergency_contact_message)

		# Return the successful HTML content and status code
		return {
			"statusCode": 200,
			"headers": { "Content-Type": "text/html" },
			"body": f"""
				{html_header}
				<section class="hero is-success mt-2">
					<div class="hero-body">
						<p class="title is-spaced has-text-white">Success!</p>
						<p class="subtitle has-text-white">The update to the settings has been successful.</p>
						<p class="subtitle has-text-white">Note that any changes to the emergency contact phone number require verification as explained in the following link:
						<a href="https://docs.aws.amazon.com/sns/latest/dg/sns-sms-sandbox-verifying-phone-numbers.html">https://docs.aws.amazon.com/sns/latest/dg/sns-sms-sandbox-verifying-phone-numbers.html</a>
						</p>
					</div>
				</section>
				{html_footer}
			"""
		}

	except Exception as e:
		logger.error(f"Error updating settings: {str(e)}")

		# Return the failed HTML content and status code
		return {
			"statusCode": 500,
			"headers": { "Content-Type": "text/html" },
			"body": f"""
				{html_header}
				<section class="hero is-danger mt-2">
					<div class="hero-body">
						<p class="title is-spaced has-text-white">Failed!</p>
						<p class="subtitle has-text-white">The update to the settings has failed: {str(e)}</p>
					</div>
				</section>
				{html_footer}
			"""
		}
