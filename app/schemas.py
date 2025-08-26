# schemas.py
# Note: This file is no longer strictly necessary for this simple example
# because the database model is defined directly in main.py

from pydantic import BaseModel

class URLBase(BaseModel):
	target_url: str

class URL(URLBase):
	is_active: bool
	clicks: int

	class Config:
		orm_mode = True

class URLInfo(URL):
	url: str
	admin_url: str
