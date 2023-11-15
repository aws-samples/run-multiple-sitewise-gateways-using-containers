# Accelerate Industry 4.0 Adoption using Containerized Gateway services

------------------------
**This is the github link for the AWS Blog post with the same name. Please refer to the blog for detailed steps with screenshots and descriptive details.**
------------------------

This project will describe how to run multiple containers on your edge gateway (AWS IoT Greengrass) to ingest data into multiple AWS accounts and/or regions. We will also have a ready to implement project using AWS Cloud Development Kit(CDK).  It is based on this (detailed) blog: Accelerate Industry 4.0 Adoption using Containerized Gateway services for AWS IoT Sitewise

# Solution Overview

## Prerequisites
1.	AWS Account   - Two AWS accounts with default VPC Subnet configuration. 

Note that the account needs to have sufficient IAM Permissions to launch Amazon EC2 instances, provision Greengrass devices, and setup AWS IoT Sitewise models and assets.

2.	AWS Cloud Development Kit [AWS CDK] installed on your local development machine (To learn more about AWS CDK examples, refer to https://cdkworkshop.com/)
3.	Docker installed on your Edge Machine (Ubuntu) running the gateway 
4.	Docker Compose to build and deploy containers


## Steps to Build

1. Provision AWS Accounts 
Provision 2 AWS Accounts - Let us call them Account A and Account B. 
Note the Account Number we will deploy the solution to.

2. Provision OPC UA Simulator Server (Amazon EC2) 

2.1 Clone the Github repository 

2.2 Modify the ```cdk.json``` file

Open the cloned repo, navigate to the iot-factory-cdk directory and open the ```cdk.json``` file 
Modify the variables in the cdk.json file for the AWS account and AWS region that you setup in Step A. This is the account A where you will deploy the Ignition Instance.

2.3	Deploy the CDK 

```
cdk deploy OPCUAInstanceStack
```

2.4	Validate the deployment

With this you have now provisioned the required cloud components in your account. You may validate this by going into your AWS Cloudformation Console and looking for a stack named OPCUAInstanceStack. 

Note the following parameters that you will use in the subsequent steps. 

```
EC2IP
EC2PublicIP
EC2Port
```


2.5	Configure the Ignition Software

You will now configure the Ignition software so that it is able to emit data from PLCs.
Launch Ignition using the URL ```http://<EC2PublicIP>/```   and login using the login using default credentials as: admin/password

You may consider setting up port forwarding as demonstrated in this blog post to avoid access to the instance from the public IP address by securely create tunnels between your instances.

Note that you may be asked for credentials when you click on any item on the webpage, when you are on it the first time.

Change the default admin credentials using the following link:https://docs.inductiveautomation.com/display/DOC79/Gateway+Security before proceeding.

Let us review the data source and simulate temperature and pressure values for two stamping presses in a production line.
1.	Create a data simulator device to represent production line 1 and two stamping presses by navigating to Config → OPC UA → Device Connections. (Note that Config is on the left menu bar)

2.	Create a new device using ```Create new Device → Programmable Device Simulator → Next``` and use Production Line 1 as name, and then hit “Create New Device”

3.	Now you will simulate the data for temperature and pressure measurements by loading an existing program. 
    a.	Choose More → edit program → Load Simulator Program → Load from CSV option
    b.	Browse to <Your clone repo>/ iot-factory-cdk/iot_factory_cdk/stacks/opcua_datasource /simulator_program_instructions.csv from and select Load Simulator Program
    c.	Choose Save Program


3.	Set up AWS IoT Sitewise Assets and Models

3.1	Deploy the CDK 

Use the following command to deploy the infrastructure on your account
```
cdk deploy SiteWiseAssetStack
```


3.2	Validate the deployment 
Let us validate that Sitewise Assets and Models have been setup correctly. From the AWS IoT SiteWise console on the Account A, select Assets and review the asset hierarchy by clicking on the “+” button near the “Sample_Site1”. 

Repeat the step 3.1 and 3.2 in Account B.


4.	Provision the required cloud and Edge components to ingest data from Ignition Server

4.1	Deploy the CDK to install the required cloud and edge components for Greengrass and Sitewise Edge

Update the ```iot-factory-cdk/env.sh``` with the following parameters
1.	Environment: Any lowercase string, for example dev
2.	OPCUAIP: The IP address of the OPCUA server - (EC2IP) from Step 2.4
3.	OPCUAPort: The port to which to connect to for the OPCUA server - (EC2Port) from Step 2.4

Use the following command to deploy the infrastructure on your account

```
source iot-factory-cdk/env.sh
cdk deploy IotFactoryCdkStack
```

Wait for the deployment to be successful. You may validate this by going into your AWS Cloudformation Console and looking for a stack named ```IotFactoryCdkStack```

4.2	Build the Docker and run the containers on the VM
In this step you will build the docker image for AWS IoT Greengrass that will run on the Edge VM.

4.3	Create the docker template

On your IDE, where you cloned the repo refer to the script ```greengrassv2-installation/docker/config_docker```.py. This script creates the ```greengrassv2-installation/docker/docker-compose.yml``` file.

Note : This file relies on parameters from the cdk.out [refer to this doc to know more about cdk assets]file so please make sure to run the script from the same environment from where your ran cdk deploy in the prior step or copy the ```cdk.out``` to the machine where you run this script.
Run the following script 
```
cd greengrassv2-installation/docker/
python3 config_docker.py
```
Check the following file: ```greengrassv2-installation/docker/docker-compose.yml``` to validate that the script completed successfully.


4.4	Build the Docker Image
You will run the script on the machine where docker daemon is running. 
This could be a machine on your on-premises data center, or an Amazon EC2 instance, that has network connectivity with both your data source (Ignition or any OPC-UA compatible server) and AWS Cloud.

```
cd greengrassv2-installation/docker/

make build
```

4.5	Run the Docker Container 
```
cd greengrassv2-installation/docker/

make start

``` 
4.6	Setup the second AWS IoT Sitewise Gateway on Account B 
Repeat steps 4 on Account B.  Make sure to modify the account number in cdk.json file as shown in 2.2
With this step you have the edge gateway running that ingests data from your ignition server and delivers it to AWS IoT Sitewise in the cloud


5.	Validate the Data Flow 

In this step, you will verify the data ingested from Ignition OPC UA server through AWS IoT SiteWise gateway in both AWS Accounts (Account A and Account B).
From the AWS IoT SiteWise console on the Account A, select Assets 
1.	Verify the near real-time temperature and pressure values for the two stamping press assets 

    a.	Navigate to Sample_Site1 → Sample_Area1 → Sample_Line1 → Sample StampingPress1

    b.	Switch to Measurements tab and look for values under Latest value column


2.	Repeat the steps for Sample_StampingPress2 asset to review the data ingestion.

You may repeat steps 1, and 2 on Account B to review the successful data ingestion into AWS IoT Sitewise on that account/region

6.	Delete the Stack
Once you have validated the results, you may delete the cdk stack to avoid incurring any additional costs.

```
cdk destroy IotFactoryCdkStack
cdk destroy SiteWiseAssetStack
cdk destroy OPCUAInstanceStack
```

# License

This library is licensed under the MIT-0 License. See the LICENSE file.

