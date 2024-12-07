# lifecheck-aws - verification, notification poller, and parameter update

## Overview

Lifecheck is a set of applications that work together to regularly confirm that a person has 'checked-in', thus indicating that the person is still alive. It has been developed to ensure that friends and family are notified if a certain time period has elapsed without a successful verification. The original intention of Lifecheck was to provide a safety net to ensure that household pets receive the care they need from friends and family if their owners should suddenly pass away.

This repository works in conjunction with the other Lifecheck repository:
* `lifecheck-client`: A Windows service that will perform verification when Windows is started. This is intended to perform automatic verification for people who restart their Windows desktops on a daily basis.

This `lifecheck-aws` project contains Python Lambda functions that will:
1. Update a `last_verification` parameter in Systems Manager Parameter Store indicating the last time a person checked in.
2. Send messages to various contacts after certain time periods have elapsed since the last check in.
3. Allow the various contact information and message content settings to be updated.

![Example 1: Lifecheck Settings](images/lifecheck-settings-1.png?raw=true)
![Example 2: Lifecheck Settings](images/lifecheck-settings-2.png?raw=true)

## Installation and usage

1. Follow the instructions below to deploy `lifecheck-aws` to AWS.
2. Add the redirect to the OAuth credentials in your new Google API using the value of the `GoogleAPIRedirectUrl` (output from the deployment) and wait for the changes to take effect.
3. Initialise contact settings by loading the `LifecheckSettingsUrl` (output from deployment) into a browser and saving the changes.
4. Install the Windows service from the `lifecheck-client` repository and in the setup use the value of `LifecheckApiKey` (output from the deployment) when configuring the service.

Lifecheck will wait for an initial period (defaulted to 30 hours) before sending an email reminder asking you to manually check in. Clicking the verification link in this email will reset the verification counter, as will restarting your Windows desktop. If you restart your Windows desktop every day, you will not receive this email. This notification is intended as a backup to automatic verification, and prevents your secondary contacts from being notified unnecessarily when you do not have access to your desktop PC.

A few hours after this (defaulted to 40 hours after the last verification), if you have not checked in, Lifecheck will send an email alert to your secondary contacts asking them to contact you.

A final message will be sent some hours after this (defaulted to 48 hours after the last verification) with an emergency message. This message will not be sent by email. Instead, it will be sent by text message using the phone number defined as your emergency contact.

### AWS associated costs

**FREE**. With a quota of 24 maximum calls per gateway per day, this application alone should never exceed the AWS free tier.

### Email and phone number verification in development environments

In a development environment, AWS requires recipient email addresses to be verified in Amazon Simple Email Service (SES) and phone numbers to prevent spam and abuse.

* Primary Contact Email: The primary contact email address (typically your own email address) will be confirmed during the application deployment process.
* Secondary Contact Email and Emergency Contact Phone Number: You can add or change secondary contact email address and emergency contact phone number using the lifecheck-settings application.

The email addresses must be manually verified by the recipients clicking a link in a verification email sent by SES. There is a similar procedure for verifying the emergency contact phone number that requires adding the phone number via the SNS console and entering a code sent to the phone.

For detailed instructions on verification refer to the official AWS documentation:
* For email addresses in SES: https://docs.aws.amazon.com/ses/latest/dg/verify-addresses-and-domains.html
* For phone numbers in SNS: https://docs.aws.amazon.com/sns/latest/dg/sns-sms-sandbox-verifying-phone-numbers.html

## Prerequisites

* **Git:** Ensure Git is installed on your Windows machine.
* **Google Account:** A Google account will be used to login to the `lifecheck-settings` application.
* **Google API Client ID:** OAuth authentication via Google will be used to allow access to the settings application. Refer to the following documentation: https://developers.google.com/identity/gsi/web/guides/get-google-api-clientid
* **AWS Account:** You'll need an AWS account to deploy and manage the Lambda function.
* **AWS SAM CLI**: Install the AWS SAM CLI. Refer to the official documentation for instructions: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html

## Setup and deployment

1. **Clone the repository:**
   * Open Git Bash.
   * Navigate to the directory where you want to store the project.
   * Clone the repository: `git clone git@github.com:andrewmelvin-dev/lifecheck-aws.git`

2. **Navigate to the project directory:**
   * `cd lifecheck-aws`

3. **Create the CloudFormation deployment template:**
   * Run the build command: `sam.cmd build`
   * Note: The command to execute the build for Windows is shown. Under Windows, the SAM CLI does not have a direct executable binary. For building on other systems the `.cmd` should be removed.
   * Note: The SAM template.yaml file may need to have its Runtime properties updated to match the specific version of Python that has been installed.

4. **Deploy to AWS:**
   * Run the deployment command: `sam.cmd deploy --guided`
   * Enter the following details into the guided deployment:
      * **Stack Name**: `lifecheck-aws`
      * **AWS Regions**: The region name that is geographically located nearby e.g. ap-southeast-2.
      * **Parameter GoogleClientId**: The client ID provided when setting up the new Google API.
      * **Parameter GoogleClientSecret**: The client secret provided when setting up the new Google API.
      * **Parameter GoogleAccountEmailAddress**: The email address of the Google account used to login to the `lifecheck-settings` application - this will also be used as the sending address for Lifecheck notifications.
      * **Parameter PrimaryContactEmailAddress**: The email address of your primary contact (typically your own email address - this will be the person that receives the first notification).
      * Answer `y` to the remaining [Y/n] questions, and keep the SAM configuration file/environment at their defaults.
      * **Deploy this changeset?**: `y`

5. **Retrieve the generated API key:**
   * Run the command shown in the `LifecheckApiKeyCLI` parameter that is output when the stack is deployed.
   * This call to the AWS apigateway service will retrieve the generated API key for the automatic verification API gateway. Make sure to note the value of the generated API key, as you'll need it when building the `lifecheck-client` Windows service.

## CloudFormation outputs

After successfully deploying the SAM template, you should see the following outputs:

| Key                        | Description                                                           | Example Value                                                               |
|----------------------------|-----------------------------------------------------------------------|-----------------------------------------------------------------------------|
| `LifecheckVerificationUrl` | URL for the POST verification API Gateway used by the Windows service | `https://zzzz123abc.execute-api.ap-southeast-2.amazonaws.com/Prod/verify`   |
| `GoogleAPIRedirectUrl`     | URL to provide for Google API redirection                             | `https://xxxx456def.execute-api.ap-southeast-2.amazonaws.com/Prod/settings` |
| `LifecheckSettingsUrl`     | URL for the settings application                                      | `https://accounts.google.com/o/oauth2/v2/auth?client_id=...`                |
| `LifecheckApiKeyCLI`       | The command to run to retrieve the generated API key from AWS         | `aws apigateway get-api-key --api-key ...`                                  |

## File overview ##

### template.yaml ###

This is the SAM template used to generate a CloudFormation template that can be used to deploy the application to AWS. It includes:

  * Three separate API Gateways with the following endpoints:
    * /verify: Handles token verification requests and updates the last verification time. This gateway is authenticated by an API key.
    * /verify-email: Handles email verification requests with a temporary token.
    * /settings: Handles requests to view the lifecheck-settings application and update the settings.
  * Six Lambda functions:
    * LifecheckVerificationHandler: Processes POST token verification requests from the lifecheck-client service.
    * LifecheckVerificationEmailHandler: Processes GET token verification requests from a URL sent in an email.
    * LifecheckNotificationHandler: Scheduled to run every 2 hours to check the last verification time and send notification emails if needed.
    * LifecheckAuthorizerHandler: An authorizer for the settings API gateway that performs OAuth authentication via Google.
    * LifecheckSettingsViewHandler: Processes GET requests for the lifecheck-settings application.
    * LifecheckSettingsUpdateHandler: Processes POST requests from the lifecheck-settings application.
  * Parameters input that will save configuration data to Parameter Store in AWS Systems Manager.
  * API key authentication and usage plans for rate limiting and quota management of the automatic verification API gateway.

### .py Python files ###

See the explanations of the Lambda functions in the template.yaml section above.

### requirements.txt ###

Dependencies used by the Python functions that will be installed and bundled by the SAM build process.

## TODO: Future enhancements/modifications ##

* Add configurable email subject.
* Allow the notification thresholds of 30, 40 and 48 hours to be configurable.
* Complete SMS notification integration for the emergency contact. There's currently a problem with phone number verification - in attempting to verify a phone number, Amazon SNS is reporting an access denied error and claiming the monthly quota for the free tier has been exceeded (despite no text messages having been sent). Notification to the emergency contact via email is not affected by this and still works as expected.
* Provide a customised gateway response for unauthorized users attempting to access the secured settings API gateway.
* Find a better solution to retrieve the value of the generated API key. The inability to output the actual generated API key (rather than its resource ID) is a shortcoming of CloudFormation that has not yet been addressed.
