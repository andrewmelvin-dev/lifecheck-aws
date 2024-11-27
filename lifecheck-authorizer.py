"""
lifecheck-authorizer.py

This script is a Lambda function that acts as an authorizer for the Settings API Gateway.
This allows authentication via Google OAuth that matches the Google account email address
originally configured as part of deployment of the SAM template.
"""

import os
import boto3
import logging
import json
import base64
import urllib.request
import urllib.parse
import google.auth
from google.auth.transport.requests import Request
from google.oauth2 import id_token

ssm = boto3.client('ssm')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# URLs to Google's public keys for OAuth2 validation and token endpoint
GOOGLE_PUBLIC_KEYS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

def lambda_handler(event, context):
	logger.info(f"Starting lambda authorisation - retrieving Google account/client details")

	# Retrieve the environment variables containing google account/client parameter names
	google_account_email_param = os.environ.get('GOOGLE_ACCOUNT_EMAIL_PARAM')
	google_client_id_param = os.environ.get('GOOGLE_CLIENT_ID_PARAM')
	google_client_secret_param = os.environ.get('GOOGLE_CLIENT_SECRET_PARAM')

	# Determine the redirect URI
	redirect_uri = f"https://{event['requestContext']['apiId']}.execute-api.{os.environ.get('REGION')}.amazonaws.com/Prod/settings"
	logger.info(f"redirect_uri='{redirect_uri}'")

	# Retrieve parameter values from Parameter Store
	try:
		response = ssm.get_parameters(
			Names=[
				google_account_email_param, 
				google_client_id_param, 
				google_client_secret_param
			],
			WithDecryption=False
		)

		params = {param['Name']: param['Value'] for param in response['Parameters'] if param is not None}
		google_account_email = params.get(google_account_email_param)
		google_client_id = params.get(google_client_id_param)
		google_client_secret = params.get(google_client_secret_param)

		if not google_account_email or not google_client_id or not google_client_secret:
			logger.error(f"Missing required parameters: google_account_email='{google_account_email}' google_client_id='{google_client_id}' google_client_secret='{google_client_secret}'")
			raise Exception(f"Missing required parameters")
	except Exception as e:
		logger.error(f"Error retrieving parameters from Parameter Store: {str(e)}")
		raise Exception(f"Error retrieving parameters from Parameter Store")

	logger.info(f"Extracting Google authorization code")

	# Extract the Google Authorization Code from query parameters
	code = event['queryStringParameters'].get('code')
	if not code:
		raise Exception("Missing Google authorization code")
	
	# Exchange the authorization code for an ID token
	token = exchange_code_for_token(code, google_client_id, google_client_secret, redirect_uri)
	
	# Validate the ID token using Google's public keys
	user_data = validate_token(token, google_client_id)
	
	# Check if the user's email is the one you expect
	if user_data.get('email') != google_account_email:
		raise Exception("Unauthorized user")

	# Create and return an IAM policy to allow the request
	return generate_policy(user_data['email'], 'Allow', event['methodArn'])

# Function to exchange the authorization code (provided by Google OAuth) for an ID token
def exchange_code_for_token(code, client_id, client_secret, redirect_uri):
	logger.info(f"Exchanging authorization code '{code}' for token")

	# Create the payload for the request to the token endpoint
	data = {
		'code': code,
		'client_id': client_id,
		'client_secret': client_secret,
		'redirect_uri': redirect_uri,
		'grant_type': 'authorization_code'
	}

	# Send the request to Google to exchange the code for a token
	data = urllib.parse.urlencode(data).encode("utf-8")
	request = urllib.request.Request(GOOGLE_TOKEN_ENDPOINT, data)
	response = urllib.request.urlopen(request)
	response_data = json.load(response)
	return response_data['id_token']

# Function to validate the ID token using Google's public keys
def validate_token(token, client_id):
	logger.info(f"Validating token '{token}'")

	# Retrieve Google's public keys
	response = urllib.request.urlopen(GOOGLE_PUBLIC_KEYS_URL)
	keys = json.load(response)
	
	# Decode and validate the ID token
	header = json.loads(base64.b64decode(token.split('.')[0] + '=='))
	key_id = header['kid']

	# Find the corresponding public key from the keys
	public_key = None
	for key in keys['keys']:
		if key['kid'] == key_id:
			public_key = key
			break

	if not public_key:
		raise Exception("Public key not found")

	# Use the public key to validate the ID token
	try:
		# Verify the token with the public key
		credentials = id_token.verify_oauth2_token(token, Request(), audience=client_id)
		# The token is valid so return the user data
		return credentials
	except Exception as e:
		raise Exception(f"Token validation failed: {str(e)}")

# Function to generate an IAM policy for the API Gateway request
def generate_policy(principal_id, effect, resource):
	# Derive the other method path (if resource is GET, create POST and vice versa)
	if "/GET" in resource:
		resource_post = resource.replace("/GET", "/POST")
		resource_get = resource
	elif "/POST" in resource:
		resource_get = resource.replace("/POST", "/GET")
		resource_post = resource
	else:
		raise ValueError("Resource path must include either '/GET' or '/POST'")

	logger.info(f"Generating IAM policy effect '{effect}' for principal '{principal_id}' and resources '{resource_get}' and '{resource_post}'")

	policy = {
		"principalId": principal_id,
		"policyDocument": {
			"Version": "2012-10-17",
			"Statement": [
				{
					"Action": "execute-api:Invoke",
					"Effect": effect,
					"Resource": [
							resource_get,
							resource_post
					]
				}
			]
		}
	}
	return policy
