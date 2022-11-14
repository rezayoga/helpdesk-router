import json
from typing import List, Any, Optional

from pydantic import BaseModel, validator, Field


class User_Detail(BaseModel):
	id: str = Field(None, alias="user_id")
	client_id: str = Field(None, alias="client_id")
	name: str = Field(None, alias="name")
	email: str = Field(None, alias="email")
	phone: str = Field(None, alias="phone")
	roles: List[str] = Field(None, alias="roles")
	title: str = Field(None, alias="title")
	avatar: str = Field(None, alias="avatar")
	mobile: str = Field(None, alias="mobile")
	modules: List[str] = Field(None, alias="modules")
	divisions: List[str] = Field(None, alias="divisions")
	last_name: str = Field(None, alias="last_name")
	first_name: str = Field(None, alias="first_name")
	display_name: str = Field(None, alias="display_name")


class User(BaseModel):
	access_token: Optional[str] = Field(None, alias="AccessToken")
	expires_in: Optional[int] = Field(None, alias="ExpiresIn")
	refresh_token: Optional[str] = Field(None, alias="RefreshToken")
	token_type: Optional[str] = Field(None, alias="TokenType")
	user: User_Detail = Field(None, alias="User")

	def __hash__(self):
		return hash("User" * self.access_token)

	class Config:
		json_encoders = {
			Any: lambda v: v.__dict__
		}


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
