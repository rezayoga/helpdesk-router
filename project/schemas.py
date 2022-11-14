import json
from typing import List, Any, Optional

from pydantic import BaseModel, validator


class User_Detail(BaseModel):
	id: Optional[str]
	client_id: Optional[str]
	name: Optional[str]
	email: Optional[str]
	phone: Optional[str]
	roles: Optional[List[str]]
	title: Optional[str]
	avatar: Optional[str]
	mobile: Optional[str]
	modules: Optional[List[str]]
	divisions: Optional[List[str]]
	last_name: Optional[str]
	first_name: Optional[str]
	display_name: Optional[str]


class User(BaseModel):
	access_token: Optional[str]
	expires_in: Optional[int]
	refresh_token: Optional[str]
	token_type: Optional[str]
	user: Optional[User_Detail]


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
				"recipients": ["b001",
				               "b002",
				               "b003"],
				"message": {"data": [
					{"type": "text", "text": "Hello World"},
					{"type": "image", "url": "https://example.com/image.png"},
					{"type": "button", "text": "Click Me", "url": "https://example.com"},
					{"type": "text", "text": "Ok World"},
					{"type": "image", "url": "https://example.com/image2.png"},
				]}
			}
		}
