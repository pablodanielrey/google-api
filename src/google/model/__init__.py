import os
from sqlalchemy import create_engine
from sqlalchemy.schema import CreateSchema
from sqlalchemy.orm import sessionmaker

from model_utils import Base

port = os.environ.get('GOOGLE_DB_PORT', 5432)

@contextlib.contextmanager
def obtener_session():
    engine = create_engine('postgresql://{}:{}@{}:{}/{}'.format(
        os.environ['GOOGLE_DB_USER'],
        os.environ['GOOGLE_DB_PASSWORD'],
        os.environ['GOOGLE_DB_HOST'],
        port,
        os.environ['GOOGLE_DB_NAME']
    ), echo=True)

    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


from .GoogleModel import GoogleModel

__all__ = [
    'GoogleModel'
]

def crear_tablas():
    from .entities import Sincronizacion, DatosDeSincronizacion
    from sqlalchemy.schema import CreateSchema

    engine = create_engine('postgresql://{}:{}@{}:{}/{}'.format(
        os.environ['GOOGLE_DB_USER'],
        os.environ['GOOGLE_DB_PASSWORD'],
        os.environ['GOOGLE_DB_HOST'],
        port,
        os.environ['GOOGLE_DB_NAME']
    ), echo=True)

    engine.execute(CreateSchema('google'))
    Base.metadata.create_all(engine)
