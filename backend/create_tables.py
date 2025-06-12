from database import Base, engine
from models.habilidad import Habilidad
from models.tiempo import TiempoCarga 

# Esta línea le dice a SQLAlchemy que cree todas las tablas definidas
Base.metadata.create_all(bind=engine)

print("Tabla habilidades creada exitosamente")
