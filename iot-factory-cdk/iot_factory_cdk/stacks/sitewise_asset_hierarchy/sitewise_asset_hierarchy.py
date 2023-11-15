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
    aws_iotsitewise as iotsitewise, Stack
)
from constructs import Construct

import uuid


class SiteWiseAsset(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        temperature_property_id = str(uuid.uuid4())
        pressure_property_id = str(uuid.uuid4())
        stamping_presses_hierarchy_id = str(uuid.uuid4())
        line_hierarchy_id = str(uuid.uuid4())
        area_hierarchy_id = str(uuid.uuid4())
        
        # Create SiteWise Asset Models
        stamping_asset_model = iotsitewise.CfnAssetModel(self, 'stamping_model', 
            asset_model_name = 'Sample_StampingPress',
            asset_model_properties = [
                iotsitewise.CfnAssetModel.AssetModelPropertyProperty(
                    data_type="DOUBLE", logical_id=temperature_property_id, name="temperature",
                    type=iotsitewise.CfnAssetModel.PropertyTypeProperty(type_name="Measurement"),
                    unit="Fahrenheit"),
                iotsitewise.CfnAssetModel.AssetModelPropertyProperty(
                    data_type="DOUBLE", logical_id=pressure_property_id, name="Pressure",
                    type=iotsitewise.CfnAssetModel.PropertyTypeProperty(type_name="Measurement"),
                    unit="kPa")
            ])
        
        line_asset_model = iotsitewise.CfnAssetModel(self, 'line_model', asset_model_name = 'Sample_Line',
                                        asset_model_hierarchies = [
                                            iotsitewise.CfnAssetModel.AssetModelHierarchyProperty(
                                                child_asset_model_id=stamping_asset_model.attr_asset_model_id,
                                                logical_id=stamping_presses_hierarchy_id,
                                                name="StampingPresses")
                                            ])
        area_asset_model = iotsitewise.CfnAssetModel(self, 'area_model', asset_model_name = 'Sample_Area',
                                        asset_model_hierarchies = [
                                            iotsitewise.CfnAssetModel.AssetModelHierarchyProperty(
                                                child_asset_model_id=line_asset_model.attr_asset_model_id,
                                                logical_id=line_hierarchy_id,
                                                name="Lines")
                                            ])
        site_asset_model = iotsitewise.CfnAssetModel(self, 'site_model', asset_model_name = 'Sample_Site',
                                        asset_model_hierarchies = [
                                            iotsitewise.CfnAssetModel.AssetModelHierarchyProperty(
                                                child_asset_model_id=area_asset_model.attr_asset_model_id,
                                                logical_id=area_hierarchy_id,
                                                name="Areas")
                                            ])

        # Create SiteWise Assets
        stamping_asset1 = iotsitewise.CfnAsset(self, 'stamping1', 
            asset_model_id = stamping_asset_model.attr_asset_model_id,
            asset_name = 'Sample_StampingPress1',
            asset_properties = [
                iotsitewise.CfnAsset.AssetPropertyProperty(
                logical_id=temperature_property_id, alias="line1/stampingpress1/temperature"),
                iotsitewise.CfnAsset.AssetPropertyProperty(
                logical_id=pressure_property_id, alias=f"line1/stampingpress1/pressure")
            ])
        stamping_asset2 = iotsitewise.CfnAsset(self, 'stamping2', 
            asset_model_id = stamping_asset_model.attr_asset_model_id,
            asset_name = 'Sample_StampingPress2',
            asset_properties = [
                iotsitewise.CfnAsset.AssetPropertyProperty(
                logical_id=temperature_property_id, alias="line1/stampingpress2/temperature"),
                iotsitewise.CfnAsset.AssetPropertyProperty(
                logical_id=pressure_property_id, alias=f"line1/stampingpress2/pressure")
            ])
        line_asset = iotsitewise.CfnAsset(self, f'line', 
                asset_model_id = line_asset_model.attr_asset_model_id,
                asset_name = f'Sample_Line1',
                asset_hierarchies=[
                    iotsitewise.CfnAsset.AssetHierarchyProperty(
                        child_asset_id=stamping_asset1.attr_asset_id,
                        logical_id=stamping_presses_hierarchy_id),
                    iotsitewise.CfnAsset.AssetHierarchyProperty(
                        child_asset_id=stamping_asset2.attr_asset_id,
                        logical_id=stamping_presses_hierarchy_id)
                    ]
                )
        area_asset = iotsitewise.CfnAsset(self, f'area', 
                asset_model_id = area_asset_model.attr_asset_model_id,
                asset_name = f'Sample_Area1',
                asset_hierarchies=[
                    iotsitewise.CfnAsset.AssetHierarchyProperty(
                        child_asset_id=line_asset.attr_asset_id,
                        logical_id=line_hierarchy_id)
                    ]
                )
        site_asset = iotsitewise.CfnAsset(self, f'site', 
                asset_model_id = site_asset_model.attr_asset_model_id,
                asset_name = f'Sample_Site1',
                asset_hierarchies=[
                    iotsitewise.CfnAsset.AssetHierarchyProperty(
                        child_asset_id=area_asset.attr_asset_id,
                        logical_id=area_hierarchy_id)
                    ]
                )