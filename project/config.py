import os
from functools import lru_cache


class BaseConfig:
	DATABASE_URL: str = ""
	DATABASE_CONNECT_DICT: dict = {}

	# CELERY_RESULT_BACKEND: str = os.environ.get("CELERY_RESULT_BACKEND", "redis://reza:reza1985@rezayogaswara.com:6379/15")
	result_backend: str = os.environ.get("CELERY_RESULT_BACKEND", "redis://reza:reza1985@rezayogaswara.com:6379/15")

	RABBITMQ_URL: str = os.environ.get("RABBITMQ_URL", "amqp://reza:reza@rezayogaswara.com:5672")
	RABBITMQ_SERVICE_PUBLISH_QUEUE_NAME = os.environ.get("RABBITMQ_SERVICE_PUBLISH_QUEUE_NAME",
	                                                     "service.queue.payload.publish")
	RABBITMQ_SERVICE_CONSUME_QUEUE_NAME = os.environ.get("RABBITMQ_SERVICE_CONSUME_QUEUE_NAME",
	                                                     "service.queue.payload.consume")

	RABBITMQ_SERVICE_QUEUE_NAME = os.environ.get("RABBITMQ_SERVICE_QUEUE_NAME", "service.queue.payload")
# CELERY_BEAT_SCHEDULE: dict = {
# 	"task-monitor-external-rabbitmq-queues": {
# 		"task": "monitor_external_rabbitmq_queues",
# 		"schedule": 5.0,  # * seconds
# 	},
# }


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
