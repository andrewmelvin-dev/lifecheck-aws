"""
lifecheck-settings-view.py

This script is a Lambda function that will provide a HTML form for the settings application.
"""

import html
import os
import boto3
import datetime
import logging

ssm = boto3.client('ssm')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):

	logger.info(f"Attempting to render the settings application")

	try:
		# Retrieve the environment variables containing parameter names
		last_verification_param = os.environ.get('LAST_VERIFICATION_PARAM')
		primary_contact_email_param = os.environ.get('PRIMARY_CONTACT_EMAIL_PARAM')
		primary_contact_message_param = os.environ.get('PRIMARY_CONTACT_MESSAGE_PARAM')
		primary_contact_datetime_param = os.environ.get('PRIMARY_CONTACT_DATETIME_PARAM')
		secondary_contact_email_param = os.environ.get('SECONDARY_CONTACT_EMAIL_PARAM')
		secondary_contact_message_param = os.environ.get('SECONDARY_CONTACT_MESSAGE_PARAM')
		secondary_contact_datetime_param = os.environ.get('SECONDARY_CONTACT_DATETIME_PARAM')
		emergency_contact_email_param = os.environ.get('EMERGENCY_CONTACT_EMAIL_PARAM')
		emergency_contact_phone_param = os.environ.get('EMERGENCY_CONTACT_PHONE_PARAM')
		emergency_contact_message_param = os.environ.get('EMERGENCY_CONTACT_MESSAGE_PARAM')
		emergency_contact_datetime_param = os.environ.get('EMERGENCY_CONTACT_DATETIME_PARAM')

		# Retrieve parameter values from Parameter Store
		logger.info(f"Attempting to retrieve parameters from the Parameter Store")

		# Retrieve the last verification separately to the following get_parameters call (which has a limit of 10 parameters)
		last_verification = None
		try:
			response = ssm.get_parameter(Name=last_verification_param, WithDecryption=False)
			last_verification_str = response['Parameter']['Value']
			if last_verification_str:
				last_verification = datetime.datetime.fromisoformat(last_verification_str)
		except ssm.exceptions.ParameterNotFound:
			logger.error(f"Parameter last_verification not found")

		response = ssm.get_parameters(
			Names=[
				primary_contact_email_param,
				primary_contact_message_param,
				primary_contact_datetime_param,
				secondary_contact_email_param,
				secondary_contact_message_param,
				secondary_contact_datetime_param,
				emergency_contact_email_param,
				emergency_contact_phone_param,
				emergency_contact_message_param,
				emergency_contact_datetime_param
			],
			WithDecryption=False
		)

		logger.info(f"Parsing parameter values")

		params = {param['Name']: param['Value'] for param in response['Parameters'] if param is not None}

		primary_contact_email = params.get(primary_contact_email_param)
		if primary_contact_email:
			primary_contact_email = html.escape(primary_contact_email)
		else:
			primary_contact_email = ""
		
		primary_contact_message = params.get(primary_contact_message_param)
		if primary_contact_message:
			primary_contact_message = html.escape(primary_contact_message)
		else:
			primary_contact_message = ""

		primary_contact_datetime = None
		primary_contact_datetime_str = params.get(primary_contact_datetime_param)
		if primary_contact_datetime_str:
			primary_contact_datetime = datetime.datetime.fromisoformat(primary_contact_datetime_str)

		secondary_contact_email = params.get(secondary_contact_email_param)
		if secondary_contact_email:
			secondary_contact_email = html.escape(secondary_contact_email)
		else:
			secondary_contact_email = ""

		secondary_contact_message = params.get(secondary_contact_message_param)
		if secondary_contact_message:
			secondary_contact_message = html.escape(secondary_contact_message)
		else:
			secondary_contact_message = ""

		secondary_contact_datetime = None
		secondary_contact_datetime_str = params.get(secondary_contact_datetime_param)
		if secondary_contact_datetime_str:
			secondary_contact_datetime = datetime.datetime.fromisoformat(secondary_contact_datetime_str)

		emergency_contact_email = params.get(emergency_contact_email_param)
		if emergency_contact_email:
			emergency_contact_email = html.escape(emergency_contact_email)
		else:
			emergency_contact_email = ""

		emergency_contact_phone = params.get(emergency_contact_phone_param)
		if emergency_contact_phone:
			emergency_contact_phone = html.escape(emergency_contact_phone)
		else:
			emergency_contact_phone = ""

		emergency_contact_message = params.get(emergency_contact_message_param)
		if emergency_contact_message:
			emergency_contact_message = html.escape(emergency_contact_message)
		else:
			emergency_contact_message = ""

		emergency_contact_datetime = None
		emergency_contact_datetime_str = params.get(emergency_contact_datetime_param)
		if emergency_contact_datetime_str:
			emergency_contact_datetime = datetime.datetime.fromisoformat(emergency_contact_datetime_str)

	except Exception as e:
		logger.error(f"Error retrieving parameters from Parameter Store: {str(e)}")
		return {
			"statusCode": 500,
			"body": f"Error retrieving parameters from Parameter Store: {str(e)}"
		}

	logger.info(f"Retrieved values from parameter store: last_verification='{last_verification}' primary_contact_datetime='{primary_contact_datetime}' primary_contact_email='{primary_contact_email}' primary_contact_message='{primary_contact_message}'")

	# Define the HTML content to return as a response
	html_content = f"""
	<!DOCTYPE html>
		<head>
			<meta charset="UTF-8">
			<meta name="viewport" content="width=device-width, initial-scale=1">
			<title>Lifecheck Settings</title>
			<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bulma@1.0.2/css/bulma.min.css">
			<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
		</head>
		<body>
			<section class="section">
				<div class="container">
					<h1 class="title is-spaced">Lifecheck Settings</h1>
					<p class="subtitle">Here you can configure who will receive alerts from the Lifecheck application.</p>
					<hr/>
					<form method="post">

						<article class="message is-dark">
							<div class="message-header"><p>Last verification/contact details</p></div>
							<div class="message-body">
								<table class="table">
									<tr>
										<th>Last Verification:</th>
										<td><span class="has-text-info">{last_verification}</span></td>
									</tr>
									<tr>
										<th>Last Primary Contact Notification:</th>
										<td><span class="has-text-info">{primary_contact_datetime}</span></td>
									</tr>
									<tr>
										<th>Last Secondary Contact Notification:</th>
										<td><span class="has-text-info">{secondary_contact_datetime}</span></td>
									</tr>
									<tr>
										<th>Last Emergency Contact Notification:</th>
										<td><span class="has-text-info">{emergency_contact_datetime}</span></td>
									</tr>
								</table>
								<span class="help">Times are shown in Greenwich Mean Time (GMT)</span>
							</div>
						</article>

						<article class="message is-info mt-4">
							<div class="message-header">
								<p>Primary Contact Details</p>
							</div>
							<div class="message-body">
								<label for="primary_contact_email" class="label">Primary Contact Email</label>
								<div class="control has-icons-left">
									<input id="primary_contact_email" name="primary_contact_email" class="input" type="email" placeholder="Enter the primary contact email address" value="{primary_contact_email}"/>
									<span class="icon is-small is-left">
										<i class="fa fa-envelope"></i>
									</span>
								</div>
								<p class="help">The primary contact is usually yourself, and will provide you with a way to perform a manual verification via email if your automatic verification isn't performed</p>
								<label for="primary_contact_message" class="label mt-2">Primary Contact Message</label>
								<div class="control">
									<textarea id="primary_contact_message" name="primary_contact_message" class="textarea" placeholder="Enter the message to send to the primary contact">{primary_contact_message}</textarea>
								</div>
								<p class="help">This message will be used when sending the initial notification to your primary email address</p>
							</div>
						</article>

						<article class="message is-warning mt-4">
							<div class="message-header">
								<p>Secondary Contact Details</p>
							</div>
							<div class="message-body">
								<label for="secondary_contact_email" class="label">Secondary Contact Email</label>
								<div class="control has-icons-left">
									<input id="secondary_contact_email" name="secondary_contact_email" class="input" type="email" placeholder="Enter the secondary contact email address" value="{secondary_contact_email}"/>
									<span class="icon is-small is-left">
										<i class="fa fa-envelope"></i>
									</span>
								</div>
								<p class="help">The secondary contact is usually a close friend or relative that will be notified if you fail to verify after 40 hours</p>
								<label for="secondary_contact_message" class="label mt-2">Secondary Contact Message</label>
								<div class="control">
									<textarea id="secondary_contact_message" name="secondary_contact_message" class="textarea" placeholder="Enter the message to send to the secondary contact">{secondary_contact_message}</textarea>
								</div>
								<p class="help">This message will be used when sending a notification to the secondary email address</p>
							</div>
						</article>

						<article class="message is-danger mt-4">
							<div class="message-header">
								<p>Emergency Contact Details</p>
							</div>
							<div class="message-body">
								<label for="emergency_contact_email" class="label">Emergency Contact Email</label>
								<div class="control has-icons-left">
									<input id="emergency_contact_email" name="emergency_contact_email" class="input" type="email" placeholder="Enter the emergency contact email address" value="{emergency_contact_email}"/>
									<span class="icon is-small is-left">
										<i class="fa fa-envelope"></i>
									</span>
								</div>
								<label for="emergency_contact_phone" class="label">Emergency Contact Phone</label>
								<div class="control has-icons-left">
									<input id="emergency_contact_phone" name="emergency_contact_phone" class="input" type="tel" placeholder="Enter the emergency contact phone number in international format e.g. +61412345678" value="{emergency_contact_phone}"/>
									<span class="icon is-small is-left">
										<i class="fa fa-phone"></i>
									</span>
								</div>
								<p class="help">The emergency contact will be notified by a text message sent to their phone if you fail to verify after 48 hours</p>
								<label for="emergency_contact_message" class="label mt-2">Emergency Contact Message</label>
								<div class="control">
									<textarea id="emergency_contact_message" name="emergency_contact_message" class="textarea" placeholder="Enter the message to send to the emergency contact">{emergency_contact_message}</textarea>
								</div>
								<p class="help">This message will be used when sending a notification to the emergency contact</p>
							</div>
						</article>

						<hr/>

						<div class="field is-grouped mt-4">
  						<div class="control"><button type="submit" class="button is-link">Update</button></div>
						</div>

					</form>
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
