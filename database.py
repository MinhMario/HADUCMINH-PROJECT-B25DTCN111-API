from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker , declarative_base
from core.config import DATABASE_URL

# ĐỌC CONFIG TỪ MÔI TRƯỜNG 
engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autoflush=False ,autocommit=False, bind=engine)


Base = declarative_base()


def get_DB ():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()