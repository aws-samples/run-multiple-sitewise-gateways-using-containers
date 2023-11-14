#!/usr/bin/env python3

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
    aws_ec2 as ec2,
    aws_iam as iam,
    Stack, CfnOutput
)
from constructs import Construct



class OPCUAInstanceStack(Stack):
    def __init__(self, scope: Construct, id: str,ami_id:str,**kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        stack = Stack.of(self)

        ignition_image = ec2.MachineImage.generic_linux({self.region: ami_id})
        # VPC
        default_vpc = ec2.Vpc.from_lookup(self, "DefaultVPC", is_default=True)
        # Security group
        ec2_security_group = ec2.SecurityGroup(self, "Ignition Security Group",
            vpc=default_vpc,
            allow_all_outbound=True
        )
        # Create a role for the instance
        iam_role = iam.Role(self, "OPCUAInstanceRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            description="Allows EC2 instance to access AWS services using IAM credentials"
            )
        iam_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"))
        # Instance
        instance = ec2.Instance(self, "Ignition_CDK"
                                ,instance_type=ec2.InstanceType("t2.medium")
                                ,machine_image=ignition_image
                                ,vpc=default_vpc
                                ,role=iam_role
                                ,security_group=ec2_security_group)
        CfnOutput(self, 'EC2IP',
            export_name = f'{stack.stack_name}-OPCUA-IP',
            value = instance.instance_private_ip
        )
        CfnOutput(self, 'EC2PublicIP',
            export_name = f'{stack.stack_name}-OPCUA-Public-IP',
            value = instance.instance_public_ip
        )
        CfnOutput(self, 'EC2Port',
            export_name = f'{stack.stack_name}-OPCUA-PORT',
            value = "62541"
        )