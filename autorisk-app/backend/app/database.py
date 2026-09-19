"""
Database connection setup.

SQLAlchemy is the "ORM" (Object-Relational Mapper) we use so our Python
code can talk to PostgreSQL using Python classes/objects instead of writing
raw SQL strings everywhere. It still runs real SQL under the hood — you can
always drop down to raw SQL when you want to (see routers/reports.py later).
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/autorisk",
)

# The "engine" manages the actual connections to Postgres.
engine = create_engine(DATABASE_URL)

# Each request gets its own database "session" (a workspace for queries).
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# All our model classes (in models.py) will inherit from this Base.
Base = declarative_base()


def get_db():
    """
    FastAPI "dependency": every route that needs the database calls
    `db: Session = Depends(get_db)` and FastAPI runs this function for us,
    handing the route a fresh session and closing it when the request ends.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
