from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Hackathon Speed Trick: Using a local SQLite file so it works instantly without setup.
SQLALCHEMY_DATABASE_URL = "sqlite:///./riversense.db"

# The engine physically connects to the database
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# A session is an active conversation with the database
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# All your database models will inherit from this Base class
Base = declarative_base()

# A dependency we will use in our routes to open/close the database connection safely
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()