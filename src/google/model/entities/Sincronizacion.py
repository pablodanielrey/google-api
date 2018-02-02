from sqlalchemy import func, Column, ForeignKey, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship

from model_utils import Base

class DatosDeSincronizacion(Base):

    __tablename__ = 'datos'
    __table_args__ = ({'schema': 'google'})

    fecha_sincronizacion = Column(DateTime)
    respuesta = Column(String)


class Sincronizacion(Base):
    ''' id es el mismo que el usuario '''

    __tablename__ = 'sincronizacion'
    __table_args__ = ({'schema': 'google'})

    dni = Column(String)
    clave_id = Column(String)
    clave = Column(String)
    clave_actualizada = Column(DateTime)
    clave_sincronizada = Column(DateTime)
    emails = Column(String)
    usuario_creado = Column(DateTime)
    usuario_actualizado = Column(DateTime)
    error = Column(Integer, default=0)

    #forzar = Column(Boolean,False)
