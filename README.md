# Serverless Image Resizing Pipeline --- Capstone Project

This capstone project implements a **fully serverless image-processing
pipeline** on AWS.\
Users can upload an image, trigger a Step Functions workflow using an
API endpoint, and automatically store a resized version in an output S3
bucket.

------------------------------------------------------------------------

## Project Overview

This pipeline performs:

1.  **Image upload** → S3 Input Bucket\
2.  **Trigger** → Step Functions (via API Gateway or manual execution)\
3.  **Processing** → Lambda with Pillow library\
4.  **Output** → S3 Output Bucket

------------------------------------------------------------------------

## 🏗 Architecture Diagram

```
       +----------------------+                     +----------------------+
       |      API Gateway     |                     |      EventBridge     |
       |      (POST /start)   |                     |   (S3 ObjectCreated) |
       +-----------+----------+                     +----------+-----------+
           |                                           |
         StartExecution                               StartExecution
           |                                           |
           v                                           v
         +----------------------+ <-------------------------+
         |    Step Functions    |      (Image Processing SM)
         +-----------+----------+
             |  Lambda Invoke
             v
           +-----+------+
           |   Lambda   |   Resize to 500px wide, JPEG
           | (Resize Fn)|
           +-----+------+
             |
             v
       +-----------------+-----------------+
       |          Amazon S3 (Buckets)      |
       |   Input (uploads)  |  Output      |
       +---------------------+--------------+

```

------------------------------------------------------------------------

## Prerequisites

-   AWS Account\
-   IAM permissions for Lambda, S3, API Gateway, Step Functions\
-   Python 3.11+\
-   Ability to upload a Lambda layer or deploy a Pillow-compatible
    package

------------------------------------------------------------------------

## S3 Setup

### 1Input Bucket

Name:

    truongbui-image-input

Folder:

    test-images/

Upload test file:

    test-images/songs.jpeg

### Output Bucket

Name:

    truongbui-image-output

------------------------------------------------------------------------

## Lambda Function Setup

Name:

    image-resize-function

Runtime:

    Python 3.12
### Layers

Name:
    
    Klayers-p312-pillow

ARN:
    
    arn:aws:lambda:ca-central-1:770693421928:layer:Klayers-p312-pillow:2

Runtime:

    python 3.12
### Environment Variables

  Key             Value
  --------------- --------------------
  OUTPUT_BUCKET   your-output-bucket

### Lambda Code

``` python
import boto3

from io import BytesIO

from PIL import Image

import os



s3 = boto3.client('s3')

OUTPUT_BUCKET = os.environ.get("OUTPUT_BUCKET")

def lambda_handler(event, context):

    bucket = event['bucket']
    key = event['key']
    try:

        # Download the image from S3
        response = s3.get_object(Bucket=bucket, Key=key)

        image_data = response['Body'].read()

        # Open the image using Pillow
        image = Image.open(BytesIO(image_data))

        # Resize the image
        new_width  = 500

        new_height = int(image.size[1] * (new_width / image.size[0]))

        image = image.resize((new_width, new_height))

        # Save the resized image to a BytesIO object
        output_stream = BytesIO()

        image.convert('RGB').save(output_stream, format="JPEG")

        output_stream.seek(0) # rewind the data

        # Upload the resized image back to S3
        output_key = 'output/' + os.path.basename(key).split('.')[0] + '_resized.jpg' # New file name

        s3.put_object(Bucket=OUTPUT_BUCKET, Key=output_key, Body=output_stream)

        print(f"Resized image uploaded to s3://{bucket}/{output_key}")

        return {

            'statusCode': 200,
            'body': f"Resized image uploaded to s3://{bucket}/{output_key}"
        }

    except Exception as e:
        print(e)
        raise e
```

------------------------------------------------------------------------

## IAM Permissions

Attach a policy to Lambda execution role:

``` json
{
	"Version": "2012-10-17",
	"Statement": [
		{
			"Effect": "Allow",
			"Action": [
				"s3:GetObject"
			],
			"Resource": "arn:aws:s3:::your-input-bucket/*"
		},
		{
			"Effect": "Allow",
			"Action": [
				"s3:PutObject"
			],
			"Resource": "arn:aws:s3:::your-output-bucket/*"
		}
	]
}
```

------------------------------------------------------------------------

## Step Functions Workflow

Create a state machine named:

    ImageProcessingStateMachine

### Definition:

``` json
{
  "Comment": "Serverless image resize workflow",
  "StartAt": "ResizeImage",
  "States": {
    "ResizeImage": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": {
        "FunctionName": "your-arn-lambda-function",
        "Payload.$": "$"
      },
      "ResultPath": "$.lambdaResult",
      "Next": "WasResizeSuccessful"
    },
    "WasResizeSuccessful": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.lambdaResult.Payload.statusCode",
          "NumericEquals": 200,
          "Next": "SuccessState"
        }
      ],
      "Default": "FailState"
    },
    "SuccessState": {
      "Type": "Succeed"
    },
    "FailState": {
      "Type": "Fail",
      "Error": "ResizeFailed",
      "Cause": "The image resize operation failed."
    }
  }
}
```

------------------------------------------------------------------------

## API Gateway Setup

### 1Create REST API

-   Resource: `/start`
-   Method: `POST`
-   Integration: **AWS Service → Step Functions → StartExecution**

### API Role
-   Name: APIGatewayToStepFunctions 
-   Permission:

``` json
{
	"Version": "2012-10-17",
	"Statement": [
		{
			"Sid": "AllowStartExecution",
			"Effect": "Allow",
			"Action": "states:StartExecution",
			"Resource": "your-arn-state-machine"
		}
	]
}
```
### Mapping Template

Go to:

`POST /start → Integration Request → Mapping Templates`

Add:

``` json
{
  "stateMachineArn": "your-arn-state-machine",
  "input": "$util.escapeJavaScript($input.body)"
}
```

### Deploy API

Stage:

    prod

Example invoke endpoint:

    https://xyz123.execute-api.ca-central-1.amazonaws.com/prod/start

------------------------------------------------------------------------

## Testing the API (Postman,...)

POST body:

``` json
{
  "bucket": "your-input-bucket",
  "key": "test-images/your-image.jpeg"
}
```

Expected result: 

-   Status code: 200 OK

``` json
{
    "executionArn": "...",
    "startDate": ...
}
```

------------------------------------------------------------------------

## EventBridge 

-   Event: Event pattern

``` json
{
  "source": ["aws.s3"],
  "detail-type": ["Object Created"],
  "resources": ["The ARN of the original bucket"]
}
```
-   Target: AWS Service -> Step Function state machine

-   Input transformer: 

    Input path:

``` json
{
    "bucket":"$.detail.bucket.name",
    "key":"$.detail.object.key",
    "size":"$.detail.object.size"
}
```
    Template:

``` json
{
    "bucket": <bucket>,
    "key": <key>,
    "size": <size>
}
```

------------------------------------------------------------------------

## License
This project is licensed under the MIT License – see the `LICENSE` file for details.
