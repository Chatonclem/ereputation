from __future__ import absolute_import, unicode_literals
from ereput.celery import app
import boto3
from TwitterAPI import TwitterAPI
from requests_aws4auth import AWS4Auth
from elasticsearch import Elasticsearch, RequestsHttpConnection
import json
import access.py

@app.task
def stream_kinesis(keyword):
    # Twitter credentials

    api = TwitterAPI(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET)

    print('--------- STARTING STTREAMING KINESIS --------')
    # AWS credentials

    kinesis = boto3.client('kinesis', aws_access_key_id= AWS_ACCESS_KEY, aws_secret_access_key= AWS_SECRET_ACCESS_KEY, region_name='eu-west-1')
    client_comprehend = boto3.client('comprehend', aws_access_key_id= AWS_ACCESS_KEY, aws_secret_access_key= AWS_SECRET_ACCESS_KEY)

    tweets = api.request('statuses/filter', {'track': keyword, 'language' : 'en'})

    for tweet in tweets:
        response_sentiment = client_comprehend.detect_sentiment(Text=tweet['text'], LanguageCode='en')
        tweet['Sentiment']  = response_sentiment
        response_key_phrases = client_comprehend.detect_key_phrases(Text=tweet['text'], LanguageCode='en')
        key_phrases = list(set([x['Text'] for x in response_key_phrases['KeyPhrases']]))
        tweet['KeyPhrases'] = key_phrases

        response_entities = client_comprehend.detect_entities(Text=tweet['text'], LanguageCode='en')
        entities = list(set([x['Text'] for x in response_entities['Entities']]))
        tweet['Entities'] = entities


        kinesis.put_record(StreamName=keyword, Data=json.dumps(tweet), PartitionKey="filler")
        print("---------- RECORD SAVED ----------")

@app.task
def create_index_elastic(keyword):
    region = 'eu-west-1' # e.g. us-west-1
    print('------- START ELASTIC JOB ----- CREATING INDEX ' + keyword)
    awsauth = AWS4Auth(AWS_ACCESS_KEY, AWS_SECRET_ACCESS_KEY, 'eu-west-1', 'es')
    host = 'https://search-ereputation-6xwzbulgnn4ebyvrp47ryvbhje.eu-west-1.es.amazonaws.com' # the Amazon ES domain, including https://

    es = Elasticsearch(
        hosts=[host],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection
    )
    es.indices.create(index=keyword, ignore=400)
    print("-------- ELASTIC INDEX CREATED ---------")

@app.task
def delivery_firehose(keyword):
    print("---------- CREATING DELIVERY STREAM -----------")
    firehose = boto3.client('firehose', aws_access_key_id= AWS_ACCESS_KEY, aws_secret_access_key= AWS_SECRET_ACCESS_KEY, region_name='eu-west-1')
    response = firehose.create_delivery_stream(
        DeliveryStreamName=keyword+'_delivery',
        DeliveryStreamType='KinesisStreamAsSource',
        KinesisStreamSourceConfiguration={
            'KinesisStreamARN': 'arn:aws:kinesis:eu-west-1:052844003169:stream/'+ keyword,
            'RoleARN': 'arn:aws:iam::052844003169:role/firehose_delivery_role'
       },
        ElasticsearchDestinationConfiguration={
            'RoleARN': 'arn:aws:iam::052844003169:role/firehose_delivery_role',
            'DomainARN': 'arn:aws:es:eu-west-1:052844003169:domain/ereputation',
            'IndexName': keyword,
            'TypeName': 'pa',
            'IndexRotationPeriod': 'OneDay',
            'S3BackupMode': 'FailedDocumentsOnly',
            'S3Configuration': {
                'RoleARN': 'arn:aws:iam::052844003169:role/firehose_delivery_role',
                'BucketARN': 'arn:aws:s3:::122230',
                'Prefix': 'logs-',
            },
        }
    )
    print("-------- DELIVERY STREAM CREATED ---------")
