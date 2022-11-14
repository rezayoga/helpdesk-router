import json
from typing import List, Any, Optional

from pydantic import BaseModel, validator, Field


class User_Detail(BaseModel):
	id: Optional[str] = Field(None, alias="user_id")
	client_id: Optional[str] = Field(None, alias="client_id")
	name: Optional[str] = Field(None, alias="name")
	email: Optional[str] = Field(None, alias="email")
	phone: Optional[str] = Field(None, alias="phone")
	roles: Optional[List[str]] = Field(None, alias="roles")
	title: Optional[str] = Field(None, alias="title")
	avatar: Optional[str] = Field(None, alias="avatar")
	mobile: Optional[str] = Field(None, alias="mobile")
	modules: Optional[List[str]] = Field(None, alias="modules")
	divisions: Optional[List[str]] = Field(None, alias="divisions")
	last_name: Optional[str] = Field(None, alias="last_name")
	first_name: Optional[str] = Field(None, alias="first_name")
	display_name: Optional[str] = Field(None, alias="display_name")


class User(BaseModel):
	access_token: Optional[str] = Field(None, alias="AccessToken")
	expires_in: Optional[int] = Field(None, alias="ExpiresIn")
	refresh_token: Optional[str] = Field(None, alias="RefreshToken")
	token_type: Optional[str] = Field(None, alias="TokenType")
	user: User_Detail = Field(None, alias="User")


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
