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
from os import path
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


# This construct creates a Greengrass v2 deployment targeted to an individual thing or thingGroup.
# @summary Creates an AWS IoT role alias and referenced IAM role with provided IAM policy.
class GreengrassV2Deployment (Construct) :
    deployment_id = ''
    iot_job_id = ''
    iot_job_arn = ''

    custom_resource_name = 'GreengrassV2DeploymentFunction'
    component_list = {}

    # @summary Constructs a new instance of the IotRoleAlias class, initializing it with variables passed by parent construct
    # @param {cdk.App} scope - represents the scope for all the resources.
    # @param {string} id - this is a scope-unique id.
    # @param {target_arn, deployment_name, component, iot_job_configuraiton, deployment_policies, app_name, tags} props - user provided props for the construct.
    # @since AWS CDK v2.22.0
    def __init__(self, scope: Construct, id: str, env: str, target_arn: str, deployment_name: str, component, iot_job_configuraiton, deployment_policies, app_name: str, cost_center: str,opcua_username_password_secret_arn: str=None, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Initialize class component list
        self.component_list = component

        # ============================================================= #
        # ==================  Stack Context Values  =================== #
        # ============================================================= #
        stack_name = Stack.of(self).stack_name
        account_id = Stack.of(self).account
        region = Stack.of(self).region
        partition = Stack.of(self).partition

        # Create Lambda role to allow Custom Lambda function to build custom resources
        lambda_role = iam.Role(
            scope = self,
            id = f'{id}GGv2LambdaRole',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            inline_policies={  # Add inline policies for iot
                'IotPolicyProvisioningPolicy':
                    iam.PolicyDocument(statements=[
                        iam.PolicyStatement(
                            actions=['iot:CancelJob', 'iot:CreateJob', 'iot:DeleteThingShadow', 'iot:DescribeJob', 'iot:DescribeThing', 'iot:DescribeThingGroup', 'iot:GetThingShadow', 'iot:UpdateJob', 'iot:UpdateThingShadow'],
                            resources=[
                                f'arn:{partition}:iot:{region}:{account_id}:*'
                            ],
                            effect=iam.Effect.ALLOW,
                        ),
                        # iam.PolicyStatement(
                        #     actions=['secretsmanager:GetSecretValue'],
                        #     resources=[
                        #         opcua_username_password_secret_arn
                        #     ],
                        #     effect=iam.Effect.ALLOW,
                        # )
                    ])
            },
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole')  # Attach service role managed policy
            ],
        )

        # Call Method to check if CDK Custom Resource Provider already exists, if so, return the provider, otherwise create a new provider
        provider = GreengrassV2Deployment.get_or_create_provider(self, id, self.custom_resource_name, lambda_role)
        
        # Custom resource Lambda role permissions 
        # Permissions for Creating or cancelling deployment - requires expanded permissions to interact with things and jobs
        provider.on_event_handler.role.add_to_principal_policy(
            iam.PolicyStatement (
                effect = iam.Effect.ALLOW,
                actions = ['greengrass:CancelDeployment', 'greengrass:CreateDeployment', 'greengrass:TagResource'],
                resources = [f'arn:{partition}:greengrass:{region}:{account_id}:deployments*']
            )
        )

        # Create Custom resource with properties value as payload to establish greengrass deployment
        custom_resource = CustomResource(self, self.custom_resource_name, 
            service_token = provider.service_token,
            properties = { 
                'StackName': stack_name,
                'TargetArn': target_arn,
                'DeploymentName': deployment_name,
                'Components': self.component_list,
                'IotJobExecution': iot_job_configuraiton if iot_job_configuraiton != None else {},
                'DeploymentPolicies': deployment_policies if deployment_policies != None else {},
                'DeploymentId': self.deployment_id,
                'Tags': { "app": app_name, "costcenter": cost_center }
            }
        )

        # class public values
        self.deployment_id = custom_resource.get_att_string('DeploymentId')
        self.iot_job_id = custom_resource.get_att_string('IotJobId')
        self.iot_job_arn = custom_resource.get_att_string('IotJobArn')

    # Method adds new component to previously initialized component list
    def addComponent (self, component):
        # obtains the key from the new component to be added
        for key in component.keys():
            # if the key already exists in the component list provide Error message and exit
            if key in self.component_list:
                print(f'Duplicate components not allowed. Component {key}, already part of deployment.')
                sys.exit(1)
            # if key is not found in component list, update the component list by adding the new component key value pair
            else:
                self.component_list.update(component)
    
    # Separate static function to create or return singleton provider
    def get_or_create_provider (self, id, resource_name, lambda_role):
        stack = Stack.of(self)
        unique_id = resource_name

        # Try to find the Provider Child Node of this stack
        existing = stack.node.try_find_child(unique_id)

        # Check if provider already exists, if not, create new provider and return it
        if existing == None:
            # create asset path to the custom resource lambda code in the /assets directory
            assetpath = (path.join(path.dirname(__file__), 'assets'))

            # create Lambda function configuration
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

            # Create provider to run the Custom Resource Lambda
            create_thing_provider = custom_resources.Provider(scope=self, 
                id = f'{id}Provider', 
                on_event_handler = event_handler,
                log_retention = logs.RetentionDays.ONE_DAY
            )

            return create_thing_provider

        else:
            # If provider exists, return existing provider
            return existing