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

# Create SDK client for iot
client = boto3.client('iot')

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
        role_alias = props['IotRoleAliasName']
        role_arn = props['IamRoleArn']
        physical_resource_id = ''
        role_alias_arn = ''
        app_name = props['AppName']
        cost_center = props['CostCenter']

        # Create Role Alias
        try:
            role_alias_response = client.create_role_alias( 
                roleAlias = role_alias, 
                roleArn = role_arn,
                tags=[
                    {
                        'Key': 'app',
                        'Value': app_name
                    },
                    {
                        'Key': 'costcenter',
                        'Value': cost_center
                    }
                ]
            )
            role_alias_arn = role_alias_response.get('roleAliasArn')
            physical_resource_id = role_alias_response.get('roleAlias')
        except Exception as error:
            print(f'Unable to create IoT role alias: {role_alias}', error)
            sys.exit(1)

        print("Output: { 'PhysicalResourceId': ", physical_resource_id, " 'Data': { 'RoleAliasArn': ", role_alias_arn, "} }")

        return { 'PhysicalResourceId': physical_resource_id, 'Data': { 'RoleAliasArn': role_alias_arn } }

# on_update provides custom resource data to return to CDK update calls
def on_update(event):
    print('Update existing resource with properties: ', event['ResourceProperties'])

    role_alias = event['ResourceProperties']['IotRoleAliasName']
    physical_resource_id = event['PhysicalResourceId']
    print('No update required for already created IoT thing group: ', role_alias)

    return { 'PhysicalResourceId': physical_resource_id, 'Data': {} }

# on_delete detaches and deletes resources for this project sub resources
def on_delete(event):
    print('Delete existing resource with properties: ', event['ResourceProperties'])

    role_alias = event['ResourceProperties']['IotRoleAliasName']
    physical_resource_id = event['PhysicalResourceId']

    # Delete Role Alias
    try:
        client.delete_role_alias(
            roleAlias = role_alias
        )
    except Exception as error:
        print(f'Unable to delete IoT role alias: {role_alias}: ', error)

    return { 'PhysicalResourceId': physical_resource_id, 'Data': {} }