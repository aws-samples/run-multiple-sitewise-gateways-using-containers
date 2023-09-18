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

import sys
import boto3

# Create SDK clients for iot and systems manager
iot_client = boto3.client('iot')
ssm_client = boto3.client('ssm')

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

        thing_name = props['ThingName']
        policy_name = props['IotPolicyName']
        policy_document = props['IotPolicy']
        stack_name = props['StackName']
        physical_resource_id = ''
        certificate_arn = ''
        certificate_pem = ''
        credential_provider_endpoint_address = ''
        data_ats_endpoint_address = ''
        parameter_private_key = f'/{stack_name}/{thing_name}/private_key'
        parameter_certificate_pem = f'/{stack_name}/{thing_name}/certificate_pem'
        policy_arn = ''
        private_key = ''
        thing_arn = ''
        app_name = props['AppName']
        cost_center = props['CostCenter']

        # Create IoT thing
        try:
            thing_response = iot_client.create_thing(
                thingName = thing_name
            )
            thing_arn = thing_response.get('thingArn')
        except Exception as error:
            print(f'Error creating thing: {thing_name}', error)
            sys.exit(1)

        # Create IoT certificate and keys
        try:
            key_and_certs_response = iot_client.create_keys_and_certificate(
                setAsActive = True
            )
            certificate_arn = key_and_certs_response.get('certificateArn')
            certificate_pem = key_and_certs_response.get('certificatePem')
            physical_resource_id = key_and_certs_response.get('certificateId')
            private_key = key_and_certs_response['keyPair'].get('PrivateKey')
            print(key_and_certs_response)
        except Exception as error:
            print('Error creating certificate and keys: ', error)
            sys.exit(1)

        # Create IoT policy
        try:
            # List all iot policies
            policy_list = (iot_client.list_policies())['policies']
            
            # If policy with requested policy name is not found in the iot policy list
            if not any(policy['policyName'] == policy_name for policy in policy_list):
                # Create policy
                policy_response = iot_client.create_policy(
                    policyName = policy_name,
                    policyDocument = policy_document,
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
            else:
                policy_response = iot_client.get_policy(
                    policyName='IotFactoryCdkStack-Greengrass-Minimal-Policy'
                )

            policy_arn = policy_response.get('policyArn')
        except Exception as error:
            print(f'Error creating policy: {policy_name}', error)
            sys.exit(1)

        # Attach certificate and policy
        try:
            iot_client.attach_policy(
                policyName = policy_name,
                target = certificate_arn
            )
        except Exception as error:
            print(f'Error attaching certificate: {certificate_arn} to policy: {policy_name}: ', error)
            sys.exit(1)

        # Attach thing and certificate
        try:
            iot_client.attach_thing_principal(
                thingName = thing_name,
                principal = certificate_arn
            )

        except Exception as error:
            print(f'Error attaching certificate: {certificate_arn} to thing: {thing_name}: ', error)
            sys.exit(1)

        # Store certificate and private key in SSM param store
        try:
            # Private Key
            ssm_client.put_parameter(
                Name = parameter_private_key,
                Description = f'Certificate private key for IoT thing {thing_name}',
                Value = private_key,
                Type = 'SecureString',
                Tags=[
                    {
                        'Key': 'app',
                        'Value': app_name
                    },
                    {
                        'Key': 'costcenter',
                        'Value': cost_center
                    }
                    
                ],
                Tier = 'Advanced'
            )

            # Certificate PEM
            ssm_client.put_parameter(
                Name = parameter_certificate_pem,
                Description = f'Certificate PEM for IoT thing {thing_name}',
                Value = certificate_pem,
                Type = 'String',
                Tags=[
                    {
                        'Key': 'app',
                        'Value': app_name
                    },
                    {
                        'Key': 'costcenter',
                        'Value': cost_center
                    }
                ],
                Tier = 'Advanced'
            )
        except Exception as error:
            print('Error creating secure string parameters: ', error)
            sys.exit(1)

        # Additional data - these calls and responses are used in other constructs or external applications
        # Get the IoT-Data endpoint
        try:
            endpoint_response = iot_client.describe_endpoint(
                endpointType = 'iot:Data-ATS'
            )
            print(f"Data endpoint response {endpoint_response}")
            data_ats_endpoint_address = endpoint_response.get("endpointAddress",None)
            
        except Exception as error:
            print('Could not obtain iot:Data-ATS endpoint: ', error)
            data_ats_endpoint_address = 'stack_error: see log files'

        # Get the Credential Provider endpoint
        try:
            cred_endpoint_response = iot_client.describe_endpoint(
                endpointType = 'iot:CredentialProvider'
            )
            print(f"Creds endpoint response {cred_endpoint_response}")
            credential_provider_endpoint_address = cred_endpoint_response.get("endpointAddress",None)
        except Exception as error:
            print('Could not obtain iot:CredentialProvider endpoint: ', error)
            credential_provider_endpoint_address = 'stack_error: see log files'

        print("Output: { 'PhysicalResourceId': ", physical_resource_id, " 'Data': { 'ThingArn': ", thing_arn, " 'ThingName': ", thing_name, " 'CertificateArn': ", certificate_arn, " 'IotPolicyArn': ", policy_arn, " 'PrivateKeySecretParameter': ", parameter_private_key, " 'CertificatePemParameter': ", parameter_certificate_pem, " 'DataAtsEndpointAddress': ", data_ats_endpoint_address, " 'CredentialProviderEndpointAddress': ", credential_provider_endpoint_address, " } }")

        return { 'PhysicalResourceId': physical_resource_id, 'Data': { 'ThingArn': thing_arn, 'ThingName': thing_name, 'CertificateArn': certificate_arn, 'IotPolicyArn': policy_arn, 'PrivateKeySecretParameter': parameter_private_key, 'CertificatePemParameter': parameter_certificate_pem, 'DataAtsEndpointAddress': data_ats_endpoint_address, 'CredentialProviderEndpointAddress': credential_provider_endpoint_address } }

def on_update(event):
    print('Update existing resource with properties: ', event['ResourceProperties'])

    thing_name = event['ResourceProperties']['ThingName']
    physical_resource_id = event['PhysicalResourceId']
    print('No update required for already created IoT thing group: ', thing_name)

    return { 'PhysicalResourceId': physical_resource_id, 'Data': {} }


def on_delete(event):
    print('Delete existing resource with properties: ', event['ResourceProperties'])

    # Delete thing, certificate, and policy in reverse order.
    # Check for modifications since create (policy versions, etc.)
    certificate_arn = event['ResourceProperties']['CertificateArn']
    thing_name = event['ResourceProperties']['ThingName']
    policy_name = event['ResourceProperties']['IotPolicyName']
    stack_name = event['ResourceProperties']['StackName']
    physical_resource_id = event['PhysicalResourceId']
    parameter_private_key = f'/{stack_name}/{thing_name}/private_key'
    parameter_certificate_pem = f'/{stack_name}/{thing_name}/certificate_pem'

    # Delete certificate and private key from SSM param store
    try:
        ssm_client.delete_parameters( Names = [ parameter_private_key, parameter_certificate_pem ] )
    except Exception as error:
        print('Unable to delete parameter store values: ', error)

    # Delete policy (prune versions, detach from targets)
    # Delete all non active policy versions
    try:
        policy_list_response = iot_client.list_policy_versions( policyName = policy_name )
        versions = policy_list_response['policyVersions']
        for version in versions:
            default_version = version.get('isDefaultVersion')
            if default_version == False:
                iot_client.delete_policy_version( policyName = policy_name, policyVersionId = version.get('versionId'))
    except Exception as error:
        print(f'Unable to delete policy versions for policy {policy_name}: ', error)

    # Detach any principals
    try:
        list_policy_targets_response = iot_client.list_targets_for_policy( policyName = policy_name )
        targets = list_policy_targets_response['targets']
        for single_target in targets:
            iot_client.detach_policy( policyName = policy_name, target = single_target )
    except Exception as error:
        print(f'Unable to detach targets from policy {policy_name}: ', error)

    # Delete policy
    try:
        iot_client.delete_policy( policyName = policy_name )
    except Exception as error:
        print(f'Unable to delete policy: {policy_name}', error)

    # Delete cert
    # Detach all policies and things from cert
    try:
        principal_things_response = iot_client.list_principal_things( principal = certificate_arn )
        things = principal_things_response['things']
        for thing in things:
            iot_client.detach_principal_things( thingName = thing, principal = certificate_arn )

        attached_policies_response = iot_client.list_attached_policies( target = certificate_arn )
        policies = attached_policies_response['policies']
        for policy in policies:
            iot_client.detach_policy( policyName = policy.get['policyName'], target = certificate_arn )
    except Exception as error:
        print(f'Unable to list or detach things or policies from certificate {certificate_arn}: ', error)

    # Update Certificate
    try:
        iot_client.update_certificate( certificateId = physical_resource_id, newStatus = 'REVOKED' )
        iot_client.delete_certificate( certificateId = physical_resource_id )
    except Exception as error:
        print(f'Unable to delete certificate {certificate_arn}: ', error)

    # Delete thing
    # Check and detach principals attached to thing
    try:
        thing_principals_response = iot_client.list_thing_principals( thingName = thing_name )
        principals = thing_principals_response['principals']
        for single_principal in principals:
            iot_client.detach_thing_principal( thingName = thing_name, principal = single_principal)
    except Exception as error:
        print('Unable to list or detach principals from {thing_name}: ', error)

    try:
        iot_client.delete_thing( thingName = thing_name)
    except Exception as error:
        print(f'Error calling iot.delete_thing() for thing {thing_name}: ', error)

    return { 'PhysicalResourceId': physical_resource_id, 'Data': {} }