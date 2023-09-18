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

import sys  # sys.path.append(1, '/path/to/app/folder')   import file   // https://stackoverflow.com/questions/4383571/importing-files-from-different-folder
from os import path 
import json
from aws_cdk import (
    Duration,
    Stack,
    CustomResource,
    aws_logs as logs,
    aws_iam as iam,
    aws_lambda as awslambda,
    custom_resources
)
from constructs import Construct

 
class IotThingCertPolicy (Construct):
    thing_arn = ''
    thing_name = ''
    iot_policy_arn = ''
    certificate_arn = ''
    certificate_pem_parameter = ''
    private_key_secret_parameter = ''
    data_ats_endpoint_address = ''
    credential_provider_endpoint_address = ''
    custom_resource_name = 'IotThingCertPolicyFunction'

    # @summary Constructs a new instance of the IotThingCertPolicy class, initializing it with variables passed by parent construct
    # @param {cdk.App} scope - represents the scope for all the resources.
    # @param {string} id - this is a scope-unique id.
    # @param {thing_name, iot_policy_name, role_alias_name, app_name} props - user provided props for the construct.
    # @since AWS CDK v2.22.0
    def __init__(self, scope: Construct, id: str, env: str, thing_name: str, iot_policy_name: str, role_alias_name: str, app_name: str, cost_center:str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # ============================================================= #
        # ==================  Stack Context Values  =================== #
        # ============================================================= #
        stack_name = Stack.of(self).stack_name
        account_id = Stack.of(self).account
        region = Stack.of(self).region
        partition = Stack.of(self).partition

        lambda_role = iam.Role(
            scope = self,
            id = f'{id}LambdaRoleThingCertPolicyRole',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            inline_policies={
                'IotPolicyProvisioningPolicy':
                    iam.PolicyDocument(statements=[
                        # Actions without resource types
                        iam.PolicyStatement(
                            actions=[
                                'iot:AttachPolicy', 'iot:AttachThingPrincipal', 'iot:DeleteCertificate', 'iot:DetachPolicy', 'iot:DetachThingPrincipal', 'iot:ListAttachedPolicies', 'iot:ListPrincipalThings', 'iot:ListThingPrincipals', 'iot:UpdateCertificate'],
                            resources=[f'arn:{partition}:iot:*:*:*'],
                            effect=iam.Effect.ALLOW,
                        ),
                        iam.PolicyStatement(
                            actions=['iot:CreateKeysAndCertificate', 'iot:ListPolicies', 'iot:GetPolicy', 'iot:DescribeEndpoint'],
                            resources=['*'],
                            effect=iam.Effect.ALLOW,
                        ),
                        # Custom resource Lambda role permissions
                        # Permissions to act on thing, certificate, and policy
                        iam.PolicyStatement (
                            effect = iam.Effect.ALLOW,
                            actions = ['iot:CreateThing', 'iot:DeleteThing'],
                            resources = [f'arn:{partition}:iot:{region}:{account_id}:thing/{thing_name}']
                        ),
                         iam.PolicyStatement (
                            effect = iam.Effect.ALLOW,
                            actions = ['greengrass:*'],
                            resources = ["*"]
                        ),
                        # Create and delete specific policy                        
                        iam.PolicyStatement (
                            effect = iam.Effect.ALLOW,
                            actions = ['iot:CreatePolicy', 'iot:DeletePolicy', 'iot:DeletePolicyVersion', 'iot:ListPolicyVersions', 'iot:ListTargetsForPolicy', 'iot:TagResource'],
                            resources = [f'arn:{partition}:iot:{region}:{account_id}:policy/{iot_policy_name}']
                        ),
                        # Create SSM Parameter
                        iam.PolicyStatement (
                            effect = iam.Effect.ALLOW,
                            actions = ['ssm:DeleteParameters', 'ssm:PutParameter', 'ssm:AddTagsToResource'],
                            resources = [
                                f'arn:{partition}:ssm:{region}:{account_id}:parameter/{stack_name}/{thing_name}/private_key',
                                f'arn:{partition}:ssm:{region}:{account_id}:parameter/{stack_name}/{thing_name}/certificate_pem'
                            ]
                        )
                    ])
            },
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole')
            ],
        )

        provider = IotThingCertPolicy.get_or_create_provider(self, id, self.custom_resource_name, lambda_role)

        greengrass_core_minimal_iot_policy = json.dumps({
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Effect': 'Allow',
                        'Action': ['iot:Connect', 'iot:Subscribe', 'iot:CreateKeysAndCertificate'],
                        'Resource': f'arn:{partition}:iot:{region}:{account_id}:*'
                    },
                    {
                        'Effect': 'Allow',
                        'Action': ['iot:Receive', 'iot:Publish'],
                        'Resource': f'arn:{partition}:iot:{region}:{account_id}:*'
                    },
                    {
                        'Effect': 'Allow',
                        'Action': ['iot:DescribeEndpoint'],
                        'Resource': '*'
                    },
                    {
                        'Effect': 'Allow',
                        'Action': ['iot:GetThingShadow', 'iot:UpdateThingShadow', 'iot:DeleteThingShadow'],
                        'Resource': [f'arn:{partition}:iot:{region}:{account_id}:thing/{thing_name}*']
                    },
                    {
                        'Effect': 'Allow',
                        'Action': 'iot:AssumeRoleWithCertificate',
                        'Resource': f'arn:{partition}:iot:{region}:{account_id}:rolealias/{role_alias_name}'
                    },
                    {
                        'Effect': 'Allow',
                        'Action': ['greengrass:GetComponentVersionArtifact', 'greengrass:ResolveComponentCandidates', 'greengrass:GetDeploymentConfiguration'],
                        'Resource': f'arn:{partition}:greengrass::{region}:{account_id}:*'
                    },
                    {
                        'Effect': 'Allow',
                        'Action': ['greengrass:*', 'iot:*'],
                        'Resource': [f'arn:{partition}:iot:{region}:{account_id}:/$aws/things/'+f'{stack_name}-ThingName-{env}*',
                        f'arn:{partition}:iot:{region}:{account_id}:thing/{thing_name}*']
                    },
                    {
                        'Effect': 'Allow',
                        'Action': ['greengrass:*'],
                        'Resource': ["*"]
                    }
                ]
            }
        )

        custom_resource = CustomResource(self, self.custom_resource_name, 
            service_token = provider.service_token,
            properties = {
                'StackName' : stack_name,
                'ThingName' : thing_name,
                'IotPolicy' : greengrass_core_minimal_iot_policy,
                'IotPolicyName' : iot_policy_name,
                'CertificateArn' : self.certificate_arn,
                'AppName' : app_name,
                'CostCenter' : cost_center
            }
        )

        # class public values
        self.certificate_pem_parameter = custom_resource.get_att_string('CertificatePemParameter')
        self.private_key_secret_parameter = custom_resource.get_att_string('PrivateKeySecretParameter')
        self.thing_arn = custom_resource.get_att_string('ThingArn')
        self.thing_name = thing_name
        self.iot_policy_arn = custom_resource.get_att_string('IotPolicyArn')
        self.certificate_arn = custom_resource.get_att_string('CertificateArn')
        self.data_ats_endpoint_address = custom_resource.get_att_string('DataAtsEndpointAddress')
        self.credential_provider_endpoint_address = custom_resource.get_att_string('CredentialProviderEndpointAddress')
    
    # Separate static function to create or return singleton provider
    def get_or_create_provider (self: Construct, id: str, resource_name: str, lambda_role):
        stack = Stack.of(self)
        unique_id = resource_name

        existing = stack.node.try_find_child(unique_id)

        if existing == None:

            assetpath = (path.join(path.dirname(__file__), 'assets'))

            event_handler = awslambda.Function(
                scope = self,
                id = f'{id}EventHandler',
                runtime = awslambda.Runtime.PYTHON_3_9,
                code = awslambda.Code.from_asset(assetpath),
                handler = 'lambda_function.on_event',
                role = lambda_role,
                timeout = Duration.minutes(15),
                log_retention = logs.RetentionDays.ONE_MONTH
            )

            create_thing_provider = custom_resources.Provider(scope=self, 
                id = f'{id}Provider', 
                on_event_handler = event_handler,
                log_retention = logs.RetentionDays.ONE_DAY
            )

            return create_thing_provider

        else:
            # Second or additional call, use existing provider
            return existing