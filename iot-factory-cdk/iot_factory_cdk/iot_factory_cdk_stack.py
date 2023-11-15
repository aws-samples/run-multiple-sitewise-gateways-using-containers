#  * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  * SPDX-License-Identifier: MIT-0
#  *
#  * Permission is hereby granted, free of charge, to any person obtaining a copy of this
#  * software and associated documentation files (the "Software"), to deal in the Software
#  * without restriction, including without limitation the rights to use, copy, modify,
#  * merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
#  * permit persons to whom the Software is furnished to do so.
#  *
#  * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
#  * INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
#  * PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
#  * HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
#  * OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
#  * SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from aws_cdk import (
    Stack,
    CfnOutput,
    aws_iam as iam,
    aws_secretsmanager as _secret,
)
import os
from constructs import Construct

# Import Stack Submodules
from iot_factory_cdk.stacks.greengrass_v2_deployment.greengrass_v2_deployment import GreengrassV2Deployment
from iot_factory_cdk.stacks.iot_role_alias.iot_role_alias import IotRoleAlias
from iot_factory_cdk.stacks.iot_thing_cert_policy.iot_thing_cert_policy import IotThingCertPolicy
from iot_factory_cdk.stacks.iot_thing_group.iot_thing_group import IotThingGroup
from iot_factory_cdk.stacks.sitewise_gateway.sitewise_gateway import SitewiseGateway

# Initial Construct parent "Stack" is being created with the name "IotFactoryCdkStack"
class IotFactoryCdkStack(Stack):
    # Constructor method for the IoTFactoryCdkStack - this method is run when the stack object is initially created in "/app.py"
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ============================================================= #
        # =============  Imported CloudFormation Values  ============== #
        # ============================================================= #
        env = os.getenv("Environment")
        # sns_email = sns_email_address.value_as_string

        app_name = f'iot-factory-app-name-{env}'
        cost_center = f'iot-factory-costcenter-{env}'
 
        # ============================================================= #
        # ==================  Stack Context Values  =================== #
        # ============================================================= #
        stack = Stack.of(self)
        region = Stack.of(self).region


        # ============================================================= #
        # ==============  Instantiation of SubModules  ================ #
        # ============================================================= #   
        # Create iot_role_alias Object from IoTRoleAlias
        greengrass_role_alias = IotRoleAlias(
            self,
            "GreenGrassRoleAlias",
            env = env,
            iot_role_alias_name = f'{stack.stack_name}-GreengrassRoleAlias-{region}-{env}',
            iam_role_name = f'{stack.stack_name}-GreengrassRole-{region}-{env}',
            iam_policy_name = f'{stack.stack_name}-DefaultPolicyForIotRoleAlias-{region}-{env}',
            app_name = app_name,
            cost_center = cost_center,
        )

        # Then create IoT thing, certificate/private key, and IoT Policy
        iot_thing_cert_policy = IotThingCertPolicy(
            self,
            'GreengrassCore',
            env = env,
            thing_name = f'{stack.stack_name}GreengrassCore-{env}',
            iot_policy_name = f'{stack.stack_name}-Greengrass-Minimal-Policy-{region}-{env}',
            role_alias_name = greengrass_role_alias.role_alias_name, 
            app_name = app_name,
            cost_center = cost_center
        )

        # Then create thing group and add thing
        deployment_group = IotThingGroup(
            self,
            'GreengrassDeploymentGroup',
            env = env,
            thing_arn = iot_thing_cert_policy.thing_arn,
            thing_group_name = f'{stack.stack_name}-Greengrass-Group-{env}',
            parent_group_name = '',
            thing_group_description = f'CloudFormation generated group for {env}',
            app_name = app_name,
            cost_center = cost_center
        )

        GreengrassV2Deployment(
            self, 
            'GreengrassDeployment',
            env = env,
            target_arn = deployment_group.thing_group_arn,
            deployment_name = f'{stack.stack_name} - Sitewise Components deployment for {env}',
            component = {
                'aws.greengrass.Nucleus': { 'componentVersion': '2.10.3' },
                'aws.iot.SiteWiseEdgeCollectorOpcua': { 'componentVersion': '2.3.0' },
                'aws.iot.SiteWiseEdgePublisher': { 'componentVersion': '2.2.3' },
                'aws.greengrass.StreamManager': { 'componentVersion': '2.1.9' }
            },
            iot_job_configuraiton = {},
            deployment_policies = {},
            app_name = app_name,
            cost_center = cost_center,
        )
        ip = os.getenv("OPCUAIP")
        port = os.getenv("OPCUAPort")

        # Create the IOT Sitewise Gateway
        SitewiseGateway(
            self, 
            'SitewiseGateway',
            env = env,
            stack_name = stack.stack_name,
            thing_name = iot_thing_cert_policy.thing_name,
            kepserver_ip = ip,
            kepserver_port = port,
            # opcua_secret_arn = opcua_username_password_secret_arn,
            app_name = app_name,
            cost_center = cost_center
        )



        # ============================================================= #
        # === Creation of Sample EC2 to run docker containers === #
        # ============================================================= #
        # Export of Stack Region for Cross stack reference
         # Greengrass Installer role (change the role name if you need)
        installer_policy_name = f'{stack.stack_name}-GreengrassInstallerRolePolicy-{region}-{env}'
        installer_iam_policy_statement =  iam.PolicyDocument(statements=[
            iam.PolicyStatement(
            actions=[ "iam:AttachRolePolicy",
                "iam:CreatePolicy",
                "iam:CreateRole",
                "iam:GetPolicy",
                "iam:GetRole",
                "iam:PassRole"
                         ],
                sid="CreateTokenExchangeRole",         
                effect=iam.Effect.ALLOW,
                resources=["*"]),
                iam.PolicyStatement(
                actions=[ "iam:AttachRolePolicy",
                "iot:AddThingToThingGroup",
                "iot:AttachPolicy",
                "iot:AttachThingPrincipal",
                "iot:CreateKeysAndCertificate",
                "iot:CreatePolicy",
                "iot:CreateRoleAlias",
                "iot:CreateThing",
                "iot:CreateThingGroup",
                "iot:DescribeEndpoint",
                "iot:DescribeRoleAlias",
                "iot:DescribeThingGroup",
                "iot:GetPolicy"
                         ],
                sid="CreateIoTResources",         
                effect=iam.Effect.ALLOW,
                resources=["*"]
                ),
                iam.PolicyStatement(
                actions=[ "greengrass:CreateDeployment",
                "iot:CancelJob",
                "iot:CreateJob",
                "iot:DeleteThingShadow",
                "iot:DescribeJob",
                "iot:DescribeThing",
                "iot:DescribeThingGroup",
                "iot:GetThingShadow",
                "iot:UpdateJob",
                "iot:UpdateThingShadow",
                "s3:*"
                         ],
                sid="DeployDevTools",         
                effect=iam.Effect.ALLOW,
                resources=["*"]
                )
        ])
        greengrass_installer_role = iam.Role(
            self, 'greengrassInstallerRole',
            assumed_by=iam.CompositePrincipal(iam.ServicePrincipal("greengrass.amazonaws.com"),iam.ServicePrincipal("ec2.amazonaws.com")),
            role_name=f'{stack.stack_name}-GreengrassInstallerRole-{region}-{env}',
            inline_policies={installer_policy_name:installer_iam_policy_statement}
        )
        greengrass_installer_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name(managed_policy_name="AmazonSSMManagedInstanceCore"))




   

        # Export of Thing Group Name for document_updater.py
        CfnOutput(self, 'ThingGroupName',
            export_name = f'{stack.stack_name}-ThingGroupName-{env}',
            value = deployment_group.thing_group_name
        )
        
        # Export of IOT Role Alias Name for document_updater.py
        CfnOutput(self, 'IotRoleAliasName',
            export_name = f'{stack.stack_name}-RoleAliasName-{env}',
            value = greengrass_role_alias.role_alias_name
        )

        # Provide Output for Role Alias ARN
        CfnOutput(self, 'RoleAliasArn',
            value = greengrass_role_alias.role_alias_arn
        )

        # Export of Thing ARN for external thing reference
        CfnOutput(self, 'ThingArn',
            export_name = f'{stack.stack_name}-ThingArn-{env}',
            value = iot_thing_cert_policy.thing_arn
        )

        # Export of Thing Name for document_updater.py
        CfnOutput(self, 'ThingName',
            export_name = f'{stack.stack_name}-ThingName-{env}',
            value = f'{stack.stack_name}-Greengrass-Core'
        )

        # Provide Output for IOT Policy Arn
        CfnOutput(self, 'IotPolicyArn',
            value = iot_thing_cert_policy.iot_policy_arn
        )

        # Export of Thing Group Name for GreenGrass role reference
        CfnOutput(self, 'IamRoleArn',
            export_name = f'{stack.stack_name}-IamRoleArn-{env}',
            value = greengrass_role_alias.iam_role_arn
        )

        # Export of Certificate Arn for additional reference
        CfnOutput(self, 'CertificateArn',
            export_name = f'{stack.stack_name}-CertificateArn-{env}',
            value = iot_thing_cert_policy.certificate_arn
        )

        # Export of Systems Manager Parameter Certificate PEM for document_updater.py
        CfnOutput(self, 'CertificatePemParameter',
            export_name = f'{stack.stack_name}-CertificatePem-{env}',
            value = iot_thing_cert_policy.certificate_pem_parameter
        )

        # Export of Systems Manager Parameter Private Key Secret Arn for document_updater.py
        CfnOutput(self, 'PrivateKeySecretParameter',
            export_name = f'{stack.stack_name}-PrivateKey-{env}',
            value = iot_thing_cert_policy.private_key_secret_parameter
        )


        # Provide Output for Data Ats Endpoint Address
        CfnOutput(self, 'DataAtsEndpointAddress',
            value = iot_thing_cert_policy.data_ats_endpoint_address
        )

        # Provide Output for Credential Provider Endpoint Address
        CfnOutput(self, 'CredentialProviderEndpointAddress',
            value = iot_thing_cert_policy.credential_provider_endpoint_address
        )