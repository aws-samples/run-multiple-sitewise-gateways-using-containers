# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import boto3
import sys

# Create SDK client for greengrassv2
client = boto3.client('greengrassv2')

# on_event is the lambda event handler entry point
def on_event(event, context):
    print(f'Received event: {event}  Received context: {context}')
    request_type = event['RequestType'].lower()
    if request_type == 'create':
        return on_create(event)
    if request_type == 'update':
        return on_update(event)
    if request_type == 'delete':
        return on_delete(event)
    print(f'Invalid request type: {request_type}')

# on_create creates all custom resources required for project
def on_create(event):
    # Check if we're failing Creates
    props = event['ResourceProperties']
    print(f'create new resource with {props=}')

    if event['ResourceProperties'].get('FailCreate', False):
        raise RuntimeError('Create failure requested, logging')
    else:
        print('Create new resource with properties: ', props)

        target_arn = props['TargetArn']
        deployment_name = props['DeploymentName']
        components = props['Components']
        tags = props['Tags']

        physical_resource_id = ''
        deployment_id = ''
        iot_job_id = ''
        iot_job_arn = ''

        # Create GreenGrass Deployment
        try:
            deployment_response = client.create_deployment(
                targetArn = target_arn,
                deploymentName = deployment_name,
                components = components,
                tags= tags
            )
            deployment_id = deployment_response.get('deploymentId')
            iot_job_id  = deployment_response.get('iotJobId')
            iot_job_arn = deployment_response.get('iotJobArn')
            physical_resource_id = deployment_response.get('deploymentId')
        except Exception as error:
            print(f'Error calling create_deployment for target ${target_arn}, error: ${error}')
            sys.exit(1)
            
        print("Output: {'PhysicalResourceId': ", physical_resource_id, " 'Data': { 'DeploymentId': ", deployment_id, " 'IotJobId': ", iot_job_id, " 'IotJobArn': ", iot_job_arn, "}")

        return { 'PhysicalResourceId': physical_resource_id, 'Data': { 'DeploymentId': deployment_id, 'IotJobId': iot_job_id, 'IotJobArn': iot_job_arn } }

# on_update provides custom resource data to return to CDK update calls
def on_update(event):
    print('Update existing resource with properties: ', event['ResourceProperties'])

    deployment_id = event['ResourceProperties']['DeploymentId']
    physical_resource_id = event['PhysicalResourceId']

    print('No update required for already created greengrass v2 deployment: ', deployment_id)

    return { 'PhysicalResourceId': physical_resource_id, 'Data': {} }

# on_delete detaches and deletes resources for this project sub resources
def on_delete(event):
    print('Delete existing resource with properties: ', event['ResourceProperties'])

    deployment_id = event['ResourceProperties']['DeploymentId']
    physical_resource_id = event['PhysicalResourceId']

    # Cancel the deployment
    try:
        deployment_cancellation_response = client.cancel_deployment(
            deploymentId = deployment_id
        )
        print(f'Successfully canceled Greengrass deployment {deployment_id}, response was: ', deployment_cancellation_response)
    except Exception as error:
        print(f'Error calling greengrassv2.CancelDeploymentCommand() for deployment id {deployment_id}, error: ', error)

    print(f'Delete Request: Greengrass deployment {deployment_id} successfully cancelled')

    return { 'PhysicalResourceId': physical_resource_id, 'Data': {} }