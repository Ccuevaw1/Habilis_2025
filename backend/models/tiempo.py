from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from database import Base

Base = declarative_base()

class TiempoCarga(Base):
    __tablename__ = "tiempos_carga"

    id = Column(Integer, primary_key=True, index=True)
    carrera = Column(String, index=True)
    tiempo_segundos = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
