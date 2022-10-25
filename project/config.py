import os
from functools import lru_cache

from kombu import Queue


def route_task(name, args, kwargs, options, task=None, **kw):
	if ":" in name:
		queue, _ = name.split(":")
		return {"queue": queue}
	return {"queue": "default"}


class BaseConfig:
	DATABASE_URL: str = ""
	DATABASE_CONNECT_DICT: dict = {}

	CELERY_BROKER_URL: str = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/15")
	# CELERY_RESULT_BACKEND: str = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/15")
	result_backend: str = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/15")

	RABBITMQ_URL: str = os.environ.get("RABBITMQ_URL", "amqp://reza:reza@rezayogaswara.com:5672")
	RABBITMQ_SERVICE_PUBLISH_QUEUE_NAME = os.environ.get("RABBITMQ_SERVICE_PUBLISH_QUEUE_NAME",
	                                                     "service.queue.payload.publish")
	RABBITMQ_SERVICE_CONSUME_QUEUE_NAME = os.environ.get("RABBITMQ_SERVICE_CONSUME_QUEUE_NAME",
	                                                     "service.queue.payload.consume")

	RABBITMQ_SERVICE_QUEUE_NAME = os.environ.get("RABBITMQ_SERVICE_QUEUE_NAME", "service.queue.payload")

	CELERY_BEAT_SCHEDULE: dict = {
		"task-monitor-external-rabbitmq-queues": {
			"task": "monitor_external_rabbitmq_queues",
			"schedule": 5.0,  # * seconds
		},
	}

	CELERY_TASK_DEFAULT_QUEUE: str = "default"

	# Force all queues to be explicitly listed in `CELERY_TASK_QUEUES` to help prevent typos
	CELERY_TASK_CREATE_MISSING_QUEUES: bool = False

	CELERY_TASK_QUEUES: list = (
		# need to define default queue here or exception would be raised
		Queue("default"),

		Queue("high_priority"),
		Queue("low_priority"),
	)

	CELERY_TASK_ROUTES = {
		"project.tasks.*": {
			"queue": "high_priority",
		},
	}

	CELERY_TASK_ROUTES = (route_task,)


class DevelopmentConfig(BaseConfig):
	pass


class ProductionConfig(BaseConfig):
	pass


class TestingConfig(BaseConfig):
	CELERY_BROKER_URL: str = os.environ.get("CELERY_BROKER_URL", "amqp://reza:reza@rezayogaswara.com:5672")
	CELERY_RESULT_BACKEND: str = os.environ.get("CELERY_RESULT_BACKEND", "redis://127.0.0.1:6379/15")


@lru_cache()
def get_settings():
	config_cls_dict = {
		"development": DevelopmentConfig,
		"production": ProductionConfig,
		"testing": TestingConfig
	}

	config_name = os.environ.get("FASTAPI_CONFIG", "development")
	config_cls = config_cls_dict[config_name]
	return config_cls()


settings = get_settings()
