# main.py
import os
import secrets
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base

# Import the Pydantic model from the schemas.py file
from . import schemas

# Load environment variables from a .env file
load_dotenv()

# --- Database Setup ---

# Define the database URL from environment variables
DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")
if not DATABASE_URL:
	raise ValueError("SQLALCHEMY_DATABASE_URL environment variable is not set.")

# Create the SQLAlchemy engine
try:
	engine = create_engine(DATABASE_URL)
	SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
	Base = declarative_base()
except Exception as e:
	raise RuntimeError(f"Could not connect to the database: {e}")


# Database model for the URL
class DBURL(Base):
	__tablename__ = "urls"
	id = Column(Integer, primary_key=True, index=True)
	key = Column(String, unique=True, index=True)
	target_url = Column(String, index=True)
	is_active = Column(Boolean, default=True)
	clicks = Column(Integer, default=0)


# Create the table if it doesn't exist
Base.metadata.create_all(bind=engine)


# Dependency to get a new database session for each request
def get_db():
	db = SessionLocal()
	try:
		yield db
	finally:
		db.close()


# --- FastAPI App Initialization ---

app = FastAPI()


# --- API Endpoints ---

# The root endpoint to check if the app is running
@app.get("/")
def read_root():
	return {"message": "Welcome to the FastAPI URL Shortener! Database is connected."}


# Endpoint to create a new short URL
# We now use the URLBase Pydantic model to read the request body
@app.post("/create_url", response_model=schemas.URLInfo)
def create_url(url: schemas.URLBase, db: Session = Depends(get_db), request: Request = None):
	# Generate a unique key for the short URL
	key = secrets.token_urlsafe(8)
	# Create a new URL entry in the database
	db_url = DBURL(key=key, target_url=url.target_url)
	db.add(db_url)
	db.commit()
	db.refresh(db_url)

	# Construct the full URL and admin URL
	full_url = f"{request.url.scheme}://{request.url.netloc}/{db_url.key}"
	admin_url = f"{request.url.scheme}://{request.url.netloc}/admin/{db_url.key}"

	return {
		"target_url": db_url.target_url,
		"is_active": db_url.is_active,
		"clicks": db_url.clicks,
		"url": full_url,
		"admin_url": admin_url
	}


# Endpoint to redirect to the target URL
@app.get("/{url_key}")
def redirect_to_url(url_key: str, request: Request, db: Session = Depends(get_db)):
	db_url = db.query(DBURL).filter(DBURL.key == url_key, DBURL.is_active).first()
	if db_url:
		# Increment the click count
		db_url.clicks += 1
		db.commit()
		return RedirectResponse(db_url.target_url)
	raise HTTPException(status_code=404, detail="URL not found")


# Endpoint to get info about a short URL (for debugging/admin)
@app.get("/info/{url_key}")
def get_url_info(url_key: str, db: Session = Depends(get_db)):
	db_url = db.query(DBURL).filter(DBURL.key == url_key).first()
	if db_url:
		return {
			"key": db_url.key,
			"target_url": db_url.target_url,
			"clicks": db_url.clicks,
			"is_active": db_url.is_active
		}
	raise HTTPException(status_code=404, detail="URL not found")
