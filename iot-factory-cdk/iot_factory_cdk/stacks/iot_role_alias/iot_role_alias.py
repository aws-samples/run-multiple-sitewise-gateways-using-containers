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

class IotRoleAlias(Construct):
    iam_role_arn = ''
    role_alias_name = ''
    role_alias_arn = ''

    custom_resource_name = 'IotRoleAliasFunction'

    #  @summary Constructs a new instance of the IotRoleAlias class, initializing it with variables passed by parent construct
    #  @param {cdk.App} scope - represents the scope for all the resources.
    #  @param {string} id - this is a scope-unique id.
    #  @param {iot_Role_alias_name, iam_role_name, iam_policy_name, app_name} props - user provided props for the construct.
    #  @since AWS CDK v2.22.0
    def __init__(self, scope: Construct, id: str, env: str, iot_role_alias_name: str, iam_role_name: str, iam_policy_name: str, app_name: str, cost_center: str,opcua_username_password_secret_arn: str=None, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # ============================================================= #
        # ==================  Stack Context Values  =================== #
        # ============================================================= #
        stack_name = Stack.of(self).stack_name
        account_id = Stack.of(self).account
        region = Stack.of(self).region
        partition = Stack.of(self).partition

        policy_name = 'IoTRoleAliasCustomLambdaPolicy'

        lambda_role = iam.Role(
            scope = self,
            id = f'{id}LambdaRole',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            inline_policies={
                'IotPolicyProvisioningPolicy':
                    iam.PolicyDocument(statements=[
                        iam.PolicyStatement(
                            sid = 'CustomResourceIoTPermissions',
                            actions=['iot:DeleteRoleAlias', 'iot:CreateRoleAlias'],
                            resources=[f'arn:{partition}:iot:{region}:{account_id}:policy/{policy_name}'],
                            effect=iam.Effect.ALLOW,
                        ),
                        iam.PolicyStatement(
                            sid = 'IAMIoTPermissions',
                            effect = iam.Effect.ALLOW,
                            actions = ['iam:CreateRole', 'iam:DeleteRole', 'iam:DeleteRolePolicy', 'iam:DetachRolePolicy', 'iam:ListAttachedRolePolicies', 'iam:ListRolePolicies', 'iam:PassRole', 'iam:PutRolePolicy'],
                            resources = [f'arn:{partition}:iam::{account_id}:role/{iam_role_name}']
                        ),
                        iam.PolicyStatement(
                            sid = 'IoTRoleAliasPermissions',
                            effect = iam.Effect.ALLOW,
                            actions = ['iot:CreateRoleAlias', 'iot:DeleteRoleAlias', 'iot:TagResource'],
                            resources = [f'arn:{partition}:iot:{region}:{account_id}:rolealias/{iot_role_alias_name}']
                        )
                    ])
            },
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole')
            ]
        )

        inline_policy_name = f'DefaultPolicyForIotRoleAlias-{region}-{env}' if iam_policy_name == None else iam_policy_name
        iam_role_name = iam_role_name if iam_role_name != None else iot_role_alias_name

        # Create IoT role policy for use by Greengrass IoT role alias
        greengrass_role_minimal_policy = iam.PolicyDocument(
            statements = [ iam.PolicyStatement (
                    effect = iam.Effect.ALLOW,
                    actions = ['logs:CreateLogGroup', 'logs:CreateLogStream', 'logs:PutLogEvents', 'logs:DescribeLogStreams'],
                    resources = [f'arn:{partition}:logs:{region}:{account_id}:*']
                ),
                iam.PolicyStatement (
                    effect = iam.Effect.ALLOW,
                    actions = ['s3:GetBucketLocation'],
                    resources = [f'arn:{partition}:s3:::*']
                ),
                iam.PolicyStatement (
                    effect = iam.Effect.ALLOW,
                    actions = ["iot:DescribeCertificate", "iot:Connect", "iot:Publish", "iot:Subscribe", "iot:Receive", "iot:DescribeEndpoint"],
                    resources = [f'arn:{partition}:iot:{region}:{account_id}:/$aws/things/'+f'{stack_name}-ThingName-{env}*']
                ),
                iam.PolicyStatement (
                    effect = iam.Effect.ALLOW,
                    actions = ["greengrass:*"],
                    resources = ["*"]
                ),

                iam.PolicyStatement (
                    sid = 'PutAssetPropertyValuesPropertyAliasAllowed',
                    effect = iam.Effect.ALLOW,
                    actions = ['iotsitewise:BatchPutAssetPropertyValue'],
                    resources = [f'arn:{partition}:iotsitewise:*:*:timeseries/*', f'arn:{partition}:iotsitewise:*:*:asset/*']
                ),
                iam.PolicyStatement (
                    effect = iam.Effect.ALLOW,
                    actions = ['ecr:GetDownloadUrlForLayer', 'ecr:BatchGetImage', 'ecr:GetAuthorizationToken'],
                    resources = [f'arn:{partition}:ecr:{region}:{account_id}:*']
                ),
                iam.PolicyStatement (
                    effect = iam.Effect.ALLOW,
                    actions = ['iotsitewise:BatchPutAssetPropertyValue', 'iotsitewise:ListAccessPolicies', 'iotsitewise:ListAssetModels', 'iotsitewise:ListAssetRelationships', 'iotsitewise:ListAssets', 'iotsitewise:ListAssociatedAssets', 'iotsitewise:ListDashboards', 'iotsitewise:ListGateways', 'iotsitewise:ListPortals', 'iotsitewise:ListProjectAssets', 'iotsitewise:ListProjects', 'iotsitewise:ListTimeSeries', 'iotsitewise:DescribeAccessPolicy', 'iotsitewise:DescribeAsset', 'iotsitewise:DescribeAssetModel', 'iotsitewise:DescribeAssetProperty', 'iotsitewise:DescribeDashboard', 'iotsitewise:DescribeDefaultEncryptionConfiguration', 'iotsitewise:DescribeGateway', 'iotsitewise:DescribeGatewayCapabilityConfiguration', 'iotsitewise:DescribeLoggingOptions', 'iotsitewise:DescribePortal', 'iotsitewise:DescribeProject', 'iotsitewise:DescribeStorageConfiguration', 'iotsitewise:DescribeTimeSeries', 'iotsitewise:GetAssetPropertyAggregates', 'iotsitewise:GetAssetPropertyValue', 'iotsitewise:GetAssetPropertyValueHistory', 'iotsitewise:GetInterpolatedAssetPropertyValue'],
                    resources = [f'arn:{partition}:iotsitewise:{region}:{account_id}:*']
                )
            ]
        )

        # Create IAM role with permissions
        iam_role = iam.Role (self, 'IamRoleGGTokenExchange',
            role_name = iam_role_name,
            assumed_by = iam.ServicePrincipal(service = 'credentials.iot.amazonaws.com'),
            description = 'Allow Greengrass token exchange service to obtain temporary credentials',
            inline_policies = {
                inline_policy_name: greengrass_role_minimal_policy
            }
        )

        provider = IotRoleAlias.get_or_create_provider(self, id, self.custom_resource_name, lambda_role)

        custom_resource = CustomResource(self, self.custom_resource_name, 
            service_token = provider.service_token,
            properties = {
                'StackName' : stack_name,
                'IotRoleAliasName' : iot_role_alias_name,
                'IamRoleArn' : iam_role.role_arn,
                'AppName' : app_name,
                'CostCenter' : cost_center
            }
        )

        # class public values
        self.iam_role_arn = iam_role.role_arn
        self.role_alias_name = iot_role_alias_name
        self.role_alias_arn = custom_resource.get_att_string('RoleAliasArn')

    def get_or_create_provider (self, id, resource_name, lambda_role):
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