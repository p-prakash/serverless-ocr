import tesserocr
import PIL.Image
import imghdr
import boto3
import os
import traceback


s3 = boto3.client('s3')
ddb = boto3.client('dynamodb')


def update_status(ok, vid, cv):
    ddb_table = os.environ['DYNAMODB_TABLE']
    try:
        if vid:
            ddb.update_item(Key={'ObjectPath': {'S': ok}},
                            UpdateExpression="set #verid = :atVid, #rtext = :atText", ExpressionAttributeValues={
                            ':atVid': {'S': vid}, ':atText': {'S': cv}}, TableName=ddb_table,
                            ExpressionAttributeNames={'#verid': 'versionid', '#rtext': 'RecognizedText'})
        else:
            ddb.update_item(Key={'ObjectPath': {'S': ok}},
                            UpdateExpression="set #rtext = :atText", ExpressionAttributeValues={
                            ':atText': {'S': cv}}, TableName=ddb_table,
                            ExpressionAttributeNames={'#rtext': 'RecognizedText'})
    except:
        print('Failed to update the DynamoDB table for object ' + ok)
        traceback.print_exc()


def lambda_handler(event, context):
    supported_formats = ['jpeg', 'png', 'tiff']
    for record in event['Records']:
        size = record['s3']['object']['size']
        s3_name = record['s3']['bucket']['name']
        s3_key = record['s3']['object']['key']
        s3_path = s3_name + '/' + s3_key
        file_local = '/tmp/' + os.path.basename(s3_key)

        if size > 15728640:
            print('S3 object s3://' + s3_path + ' larger than 50MB, hence did not process')

        try:
            s3_vid = record['s3']['object']['versionId']
        except KeyError:
            s3_vid = ''

        try:
            if s3_vid:
                s3.download_file(s3_name, s3_key, file_local, ExtraArgs={'VersionId': s3_vid})
            else:
                s3.download_file(s3_name, s3_key, file_local)
        except:
            print('Failed to download the S3 object: s3://' + s3_path)
            traceback.print_exc()
            continue

        try:
            ftype = imghdr.what(file_local)
            if ftype not in supported_formats:
                print('S3 object s3://' + s3_path + ' is not one of the supported image format.')
                continue
            print('S3 object s3://' + s3_path + ' is of file type ' + ftype)
        except:
            print('Failed to check the format of the S3 object: s3://' + s3_path)
            traceback.print_exc()
            continue

        try:
            print('Going to recognize ' + file_local)
            rec_text = tesserocr.image_to_text(PIL.Image.open(file_local))
            update_status(s3_path, s3_vid, rec_text)

        except:
            print('OCR failed to recognize the S3 object: s3://' + s3_path)
            traceback.print_exc()
            continue

