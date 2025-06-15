from sqlalchemy import Column, Integer, String, Float, DateTime
from database import Base
from datetime import datetime, timezone

class TiempoCarga(Base):
    __tablename__ = "tiempos_carga"

    id = Column(Integer, primary_key=True, index=True)
    carrera = Column(String, nullable=False)
    inicio = Column(DateTime(timezone=True), nullable=False)
    fin = Column(DateTime(timezone=True), nullable=False)
    tiempo_segundos = Column(Float, nullable=False)
    fecha = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))