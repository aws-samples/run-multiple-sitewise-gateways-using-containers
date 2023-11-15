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

class IotThingGroup(Construct):  # (Stack)
    thing_group_name = ''
    thing_group_arn = ''
    thing_group_id = ''

    thing_arn_list = []
    custom_resource_name = 'IotThingGroupFunction'

    # @summary Constructs a new instance of the IotRoleAlias class, initializing it with variables passed by parent construct
    # @param {cdk.App} scope - represents the scope for all the resources.
    # @param {string} id - this is a scope-unique id.
    # @param {thing_group_name, parent_group_name, thing_group_description, app_name} props - user provided props for the construct.
    # @since AWS CDK v2.22.0
    def __init__(self, scope: Construct, id: str, env: str, thing_arn: str, thing_group_name: str, parent_group_name: str, thing_group_description: str, app_name: str, cost_center: str, **kwargs) -> None:  # thing_list,
        super().__init__(scope, id, **kwargs)

        self.thing_group_name = thing_group_name
        self.parent_group_name = parent_group_name
        self.thing_group_description = thing_group_description
        self.thing_arn_list = [thing_arn]

        # ============================================================= #
        # ==================  Stack Context Values  =================== #
        # ============================================================= #
        stack_name = Stack.of(self).stack_name
        account_id = Stack.of(self).account
        region = Stack.of(self).region
        partition = Stack.of(self).partition

        lambda_role = iam.Role(
            scope = self,
            id = f'{id}ThingGroupLambdaRole',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            inline_policies={
                'IotPolicyProvisioningPolicy':
                    iam.PolicyDocument(statements=[
                        iam.PolicyStatement(
                            actions=[
                                'iot:AddThingToThingGroup',
                                'iot:TagResource'
                            ],
                            resources=[
                                f'arn:{partition}:iot:{region}:{account_id}:*'
                            ],
                            effect=iam.Effect.ALLOW,
                        ),
                        # Custom resource Lambda role permissions
                        # Permissions for the resource specific calls
                        iam.PolicyStatement (
                            effect = iam.Effect.ALLOW,
                            actions = ['iot:CreateThingGroup', 'iot:DeleteThingGroup'],
                            resources = [f'arn:{partition}:iot:{region}:{account_id}:thinggroup/{thing_group_name}']
                        )
                    ])
            },
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole')
            ],
        )

        provider = IotThingGroup.get_or_create_provider(self, id, self.custom_resource_name, lambda_role)

        custom_resource = CustomResource(self, self.custom_resource_name, 
            service_token = provider.service_token,
            properties = {
                'StackName' : stack_name,
                'ThingGroupName' : self.thing_group_name,
                'ThingGroupDescription' : self.thing_group_description,
                'ThingArnList' : self.thing_arn_list,
                'AppName' : app_name,
                'CostCenter' : cost_center
            }
        )

        # class public values
        self.thing_group_name = custom_resource.get_att_string('ThingGroupName')
        self.thing_group_arn = custom_resource.get_att_string('ThingGroupArn')
        self.thing_group_id = custom_resource.get_att_string('ThingGroupId')

    # methods
    def addThing(self, thing_arn):
        self.thing_arn_list.append(thing_arn)

    # Separate static function to create or return singleton provider
    def get_or_create_provider (self, id, resource_name, lambda_role):
        stack = Stack.of(self)
        unique_id = resource_name

        existing = stack.node.try_find_child(unique_id)

        if existing == None:

            assetpath = path.join(path.dirname(__file__), 'assets')

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
