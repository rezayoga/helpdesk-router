import json

from celery import shared_task
from pyrabbit import Client


@shared_task(name="monitor_external_rabbitmq_queues")
def monitor_external_rabbitmq_queues():
	cl = Client('rezayogaswara.com:15672', 'reza', 'reza')
	queues = [q['name'] for q in cl.get_queues()]
	return json.dumps(queues)
