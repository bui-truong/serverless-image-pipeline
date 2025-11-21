import boto3

from io import BytesIO

from PIL import Image

import os



s3 = boto3.client('s3')

OUTPUT_BUCKET = os.environ.get("OUTPUT_BUCKET")

def lambda_handler(event, context):

    bucket = event['Records'][0]['s3']['bucket']['name']

    key = event['Records'][0]['s3']['object']['key']

    size = event['Records'][0]['s3']['object']['size']



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