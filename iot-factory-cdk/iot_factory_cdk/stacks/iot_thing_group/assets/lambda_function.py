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

from typing import Any
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
    props = event['ResourceProperties']
    print(f'create new resource with {props=}')

    if event['ResourceProperties'].get('FailCreate', False):
        raise RuntimeError('Create failure requested, logging')
    else:
        print('Create new resource with properties: ', props)

        thing_group_name = props['ThingGroupName']
        thing_group_description = props['ThingGroupDescription']
        thing_arn_list = props['ThingArnList']
        app_name = props['AppName']
        cost_center = props['CostCenter']

        physical_resource_id = ''
        group_arn = ''
        group_id = ''

        # create thing group
        try:
            thing_group_response = client.create_thing_group(
                thingGroupName = thing_group_name,
                thingGroupProperties = {
                    'thingGroupDescription': thing_group_description,
                },
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
            group_arn = thing_group_response.get('thingGroupArn')
            group_id = thing_group_response.get('thingGroupId')
            physical_resource_id = group_id
        except Exception as error:
            print(f'Unable to create thing group: {thing_group_name}', error)
            sys.exit(1)

        # Add thing(s) to group
        try:
            for thing in thing_arn_list:
                client.add_thing_to_thing_group( thingGroupName = thing_group_name, thingArn = thing)
        except Exception as error:
            print(f'Error adding things {thing_arn_list=} to thing group {thing_group_name}: ', error)
            sys.exit(1)

        print("Output: { 'PhysicalResourceId': ", physical_resource_id, " 'Data': { 'ThingGroupName': ", thing_group_name, " 'ThingGroupArn': ", group_arn, " 'ThingGroupId': ", group_id, "} }")

        return { 'PhysicalResourceId': physical_resource_id, 'Data': { 'ThingGroupName': thing_group_name, 'ThingGroupArn': group_arn, 'ThingGroupId': group_id } }

# on_update provides custom resource data to return to CDK update calls
def on_update(event):
    print('Update existing resource with properties: ', event['ResourceProperties'])

    thing_group_name = event['ResourceProperties']['ThingGroupName']
    physical_resource_id = event['PhysicalResourceId']
    print('No update required for already created IoT thing group: ', thing_group_name)

    return { 'PhysicalResourceId': physical_resource_id, 'Data': {} }

# on_delete detaches and deletes resources for this project sub resources
def on_delete(event):
    print('Delete existing resource with properties: ', event['ResourceProperties'])

    thing_group_name = event['ResourceProperties']['ThingGroupName']
    physical_resource_id = event['PhysicalResourceId']

    # delete thing group
    try:
        client.delete_thing_group(
            thingGroupName = thing_group_name
        )
    except Exception as error:
        print(f'Unable to delete thing group {thing_group_name}: ', error)

    return { 'PhysicalResourceId': physical_resource_id, 'Data': {} }