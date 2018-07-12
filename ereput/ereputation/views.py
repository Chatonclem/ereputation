from django.http import HttpResponse
from django.shortcuts import render
from .forms import KeywordForm
from django.http import HttpResponseRedirect
import requests
import boto3
import time
from ereputation.tasks import stream_kinesis, create_index_elastic, delivery_firehose

def keyword(request):
	if request.method == 'POST':
		form = KeywordForm(request.POST or None)
		keyword = request.POST.get("keyword")
		create_stream(keyword)
		create_index_elastic.delay(keyword)
		time.sleep(15)
		delivery_firehose.delay(keyword)
		time.sleep(20)
		stream_kinesis.delay(keyword)
		return render(request, "ereputation/next.html", locals())
	else:
		form = KeywordForm(request.POST or None)
		return render(request, "ereputation/keyword.html", locals())

def next(request):
	return render(request, "ereputation/next.html", locals())

def create_stream(keyword):
	client = boto3.client('kinesis', region_name='eu-west-1')
	response = client.create_stream(
	   StreamName= keyword,
	   ShardCount=4
	)
