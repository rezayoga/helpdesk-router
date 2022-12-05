import json
from typing import List, Any, Optional

from pydantic import BaseModel, validator


class User_Detail(BaseModel):
	id: Optional[str] = None
	client_id: Optional[str] = None
	name: Optional[str] = None
	email: Optional[str] = None
	phone: Optional[str] = None
	roles: Optional[List[str]] = None
	title: Optional[str] = None
	avatar: Optional[str] = None
	mobile: Optional[str] = None
	modules: Optional[List[str]] = None
	divisions: Optional[List[str]] = None
	last_name: Optional[str] = None
	first_name: Optional[str] = None
	display_name: Optional[str] = None


class User(BaseModel):
	access_token: Optional[str] = None
	expires_in: Optional[int] = None
	refresh_token: Optional[str] = None
	token_type: Optional[str] = None
	user: Optional[User_Detail] = None


class UserValidation(BaseModel):
	"""Request model for /validate endpoint.
	"""

	is_validated: bool
	user: Optional[User] = None


class Payload(BaseModel):
	broadcast: bool
	recipients: List[str]
	message: Any = None

	@validator("recipients")
	def recipients_must_be_list(cls, v):
		if not isinstance(v, list):
			raise ValueError("recipients must be a list")
		return v

	@validator("message")
	def message_must_be_json_serializable(cls, v):
		try:
			json.dumps(v)
		except TypeError:
			raise ValueError("message must be JSON serializable")
		return v

	@validator('message')
	def prevent_none(cls, v):
		assert v is not None, 'message may not be None'
		return v

	@validator("broadcast")
	def broadcast_must_be_boolean(cls, v):
		if not isinstance(v, bool):
			raise ValueError("broadcast must be a boolean")
		return v

	class Config:
		schema_extra = {
			"example": {
				"broadcast": True,
				"recipients": ["b4825c7863c411ed8b03c55baead42b3",
				               "f625487c63c211ed8b03c55baead42b3",
				               "df84fd24c70f11eca0b8a95aa68aa97c",
				               "6dbebafe631811eda0bca95aa68aa97c"],
				"message": {"data": [
					{"type": "text", "text": "Hello World"},
					{"type": "image", "url": "https://example.com/image.png"},
					{"type": "button", "text": "Click Me", "url": "https://example.com"},
					{"type": "text", "text": "Ok World"},
					{"type": "image", "url": "https://example.com/image2.png"},
				]}
			}
		}
