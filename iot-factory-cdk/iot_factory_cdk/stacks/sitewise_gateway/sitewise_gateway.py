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

from os import path
import json
from aws_cdk import (
    CfnTag,
    aws_iotsitewise as sitewise
)
from constructs import Construct


class SitewiseGateway(Construct):

    def __init__(self, scope: Construct, id: str, env: str, stack_name: str, thing_name: str, kepserver_ip: str, kepserver_port: str, app_name: str, cost_center: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        # print(f"Input IP and Port {kepserver_ip} and {kepserver_port} and env {env}")
        # ============================================================= #
        # =============  SiteWise Gateway Infrastructure  ============= #
        # ============================================================= #        
        sitewise.CfnGateway(self, 'SitewiseGateway',
            gateway_name = f'{stack_name}GreenGrassCore-Gateway-{env}',
	        gateway_platform = sitewise.CfnGateway.GatewayPlatformProperty(
                greengrass_v2 = sitewise.CfnGateway.GreengrassV2Property(
                    core_device_thing_name = thing_name
                )
            ),
            gateway_capability_summaries=[sitewise.CfnGateway.GatewayCapabilitySummaryProperty(
                capability_namespace = 'iotsitewise:opcuacollector:2',
                capability_configuration = json.dumps(
                        {
                            'sources': [{
                                'name': 'OPC-UA Server',
                                'endpoint': {
                                    'certificateTrust': { 'type': 'TrustAny' },
                                    'endpointUri': 'opc.tcp://{}:{}'.format(kepserver_ip, kepserver_port),
                                    'securityPolicy': 'BASIC256_SHA256',
                                    'messageSecurityMode': 'SIGN_AND_ENCRYPT',
                                    'identityProvider':{'type':'Anonymous'},
                                    'nodeFilterRules':[]
                                },
                                'measurementDataStreamPrefix': ''
                            }]
                        }
                    )
                ),
                sitewise.CfnGateway.GatewayCapabilitySummaryProperty(
                    capability_namespace='iotsitewise:publisher:2',

                    capability_configuration = json.dumps(
                        {
                            'SiteWisePublisherConfiguration': {
                                'publishingOrder': 'TIME_ORDER'
                            }
                        }
                    )
                )
            ],
            tags=[
                CfnTag(
                    key ='app',
                    value = app_name
                )
            ]
        )
