from database import Base, engine
from models.habilidad import Habilidad

# Esta línea le dice a SQLAlchemy que cree todas las tablas definidas
Base.metadata.create_all(bind=engine)

print("Tabla habilidades creada exitosamente")
