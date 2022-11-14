import os
from functools import lru_cache
from urllib.parse import quote_plus


class BaseConfig:
	DATABASE_URL: str = ""
	DATABASE_CONNECT_DICT: dict = {}

	# CELERY_RESULT_BACKEND: str = os.environ.get("CELERY_RESULT_BACKEND",
	# "redis://reza:reza1985@192.168.217.3:6379/15")
	result_backend: str = os.environ.get("CELERY_RESULT_BACKEND", "redis://reza:reza1985@103.41.204.222:6379/15")

	RABBITMQ_URL: str = os.environ.get("RABBITMQ_URL", f"amqp://admin:{quote_plus('Coster4dm1nP@ssw0rd')}@192.168.217.3:5672")

	RABBITMQ_SERVICE_QUEUE_NAME = os.environ.get("RABBITMQ_SERVICE_QUEUE_NAME", "service.queue.payload")


class DevelopmentConfig(BaseConfig):
	pass


class ProductionConfig(BaseConfig):
	pass


class TestingConfig(BaseConfig):
	CELERY_BROKER_URL: str = os.environ.get("CELERY_BROKER_URL", f"amqp://admin:{quote_plus('Coster4dm1nP@ssw0rd')}@192.168.217.3:5672")
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
