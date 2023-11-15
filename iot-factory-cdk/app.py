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
import os

import aws_cdk as cdk

from iot_factory_cdk.iot_factory_cdk_stack import IotFactoryCdkStack
from iot_factory_cdk.stacks.opcua_datasource.opcua_datasource import OPCUAInstanceStack
from iot_factory_cdk.stacks.sitewise_asset_hierarchy.sitewise_asset_hierarchy import SiteWiseAsset


app = cdk.App()

# env = app.node.try_get_context("env")
account = app.node.try_get_context("account")
region = app.node.try_get_context("region")
ami_id = app.node.try_get_context("amiId")



opcua_datasource = OPCUAInstanceStack(app, "OPCUAInstanceStack",ami_id=ami_id,env={'account': account, 
                      'region': region})


sitewise_assets_stack = SiteWiseAsset(app, "SiteWiseAssetStack",env={'account': account, 
                      'region': region})

iot_stack = IotFactoryCdkStack(app, "IotFactoryCdkStack",
                   env={'account': account, 
                      'region': region}
            )


app.synth()
