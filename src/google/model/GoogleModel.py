from sqlalchemy import or_, func, and_
from sqlalchemy.orm import joinedload
from google.model.GoogleAuthApi import GAuthApis

import os
import uuid
import requests
from dateutil.parser import parse
import datetime
import hashlib
from apiclient import errors
import time
import logging
logging.getLogger().setLevel(logging.DEBUG)

from . import Session
from .entities import *

class GoogleModel:

    sileg_url = os.environ['SILEG_API_URL']

    @staticmethod
    def _aplicar_filtros_comunes(q, offset, limit):
        q = q.offset(offset) if offset else q
        q = q.limit(limit) if limit else q
        return q


    @classmethod
    def actualizarUsuarios(cls, uid=None):
        usuarios = []
        session = Session()
        try:
            if uid:
                params = {'c':True}
                resp = requests.get(cls.sileg_url + '/usuarios/'+ uid, params=params)
                if resp.status_code == 200:
                    datos = resp.json()
                    if 'usuario' in datos:
                        usuarios.append(datos['usuario'])
            else:
                result = session.query(func.max(Sincronizacion.actualizado)).first()
                result = result if result[0] else session.query(func.max(Sincronizacion.creado)).first()
                fecha = result[0]
                q = '{}{}'.format(cls.sileg_url, '/usuarios/')
                params = {'c':True}
                if fecha:
                    params['f'] = fecha - datetime.timedelta(hours=24)
                else:
                    params['f'] = datetime.datetime.now() - datetime.timedelta(days=9000)
                resp = requests.get(q, params=params)
                if resp.status_code == 200:
                    susuarios = resp.json()
                    usuarios = [u['usuario'] for u in susuarios]

            ignorados = []
            actualizados = []
            creados = []
            for u in usuarios:
                emails = []
                if 'mails' in u:
                    #emails = [m['email'] for m in u['mails'] if 'econo.unlp.edu.ar' in m['email'] and 'fecha_confirmado' in m and m['fecha_confirmado'] != None]
                    #CAMBIAR!!!!!! TODO
                    # en vez de lo de arriba ahora necesario para los sistemas viejos que usan el booleano en vez de la fecha de confirmado
                    for m in u['mails']:
                        if 'eliminado' in m and m['eliminado'] != None:
                            continue
                        if 'econo.unlp.edu.ar' in m['email']:
                            if 'fecha_confirmado' in m and m['fecha_confirmado'] != None:
                                emails.append(m['email'])
                            elif 'confirmado' in m and m['confirmado']:
                                emails.append(m['email'])


                clave = None
                if 'claves' in u:
                    clave = u['claves'][0] if len(u['claves']) > 0 else None

                if clave is None:
                    ignorados.append('{} - clave nula'.format(u['dni']))
                    continue

                if len(emails) <= 0:
                    ignorados.append('{} - sin mails'.format(u['dni']))
                    continue

                emails = ",".join([x for x in sorted(emails)])
                clave_actualizada = parse(clave['actualizado']) if clave['actualizado'] and clave['actualizado'] != 'null' else parse(clave['creado'])

                sinc = session.query(Sincronizacion).filter(Sincronizacion.id == u['id']).first()
                if sinc:
                    ''' actualizo los datos que fueron modificados '''
                    modificado = False
                    if sinc.clave != clave['clave']:
                        sinc.clave = clave['clave']
                        sinc.clave_actualizada = clave_actualizada
                        sinc.clave_id = clave['id']
                        actualizados.append('{} - clave'.format(u['dni']))

                    if emails != sinc.emails:
                        sinc.emails = emails
                        actualizados.append('{} - email'.format(u['dni']))

                else:
                    ''' crear usuario '''
                    s = Sincronizacion(
                        id=u['id'],
                        dni=u['dni'],
                        clave_id=clave['id'],
                        clave=clave['clave'],
                        clave_actualizada=parse(clave['actualizado']) if clave['actualizado'] and clave['actualizado'] != 'null' else parse(clave['creado']),
                        emails=emails
                    )
                    session.add(s)
                    creados.append(u['dni'])

                session.commit()

            return {'analizados':[u['dni'] for u in usuarios], 'actualizados':actualizados, 'creados':creados, 'ignorados':ignorados}
        finally:
            session.close()

    @classmethod
    def sincronizarClaves(cls):
        session = Session()
        try:
            q = session.query(Sincronizacion).filter(or_(Sincronizacion.clave_sincronizada == None, Sincronizacion.clave_sincronizada < Sincronizacion.clave_actualizada))

            sync = []
            noSync = []
            service = GAuthApis.getServiceAdmin()
            fecha = datetime.datetime.now()
            for s in q:
                if s.error >= 5:
                    ''' no intento sincronizar los que continuen con errores '''
                    continue

                userGoogle = s.dni + '@econo.unlp.edu.ar'
                try:
                    #update user
                    r = service.users().update(userKey=userGoogle,body={"password":s.clave}).execute()
                    qq = session.query(Sincronizacion).filter(Sincronizacion.id == s.id)
                    ss = qq.all()[0]
                    ss.clave_sincronizada = fecha

                    ds = cls._crearLog(r)
                    session.add(ds)

                    session.commit()
                    sync.append(s.dni)

                except errors.HttpError as err:
                    logging.exception(err)

                    ds = cls._crearLog(err)
                    session.add(ds)
                    session.commit()

                    s.error = s.error + 1
                    session.commit()

                    noSync.append(s.dni)

            return {'sincronizados':sync, 'noSincronizados':noSync}
        finally:
            session.close()

    @classmethod
    def _crearLog(cls, r):
        return DatosDeSincronizacion(
                    id= str(uuid.uuid4()),
                    fecha_sincronizacion=datetime.datetime.now(),
                    respuesta=str(r)
                )

    @classmethod
    def sincronizarUsuarios(cls):

        session = Session()
        try:
            q = session.query(Sincronizacion).filter(or_(Sincronizacion.usuario_creado == None,
                and_(Sincronizacion.usuario_actualizado == None, Sincronizacion.actualizado > Sincronizacion.usuario_creado),
                Sincronizacion.actualizado > Sincronizacion.usuario_actualizado
                ))

            creados = []
            actualizados = []
            service = GAuthApis.getServiceAdmin()
            fecha = datetime.datetime.now()

            for s in q:

                if s.error > 5:
                    ''' ignoro los registros que tengan errores '''
                    continue

                userGoogle = s.dni + '@econo.unlp.edu.ar'
                r = requests.get(cls.sileg_url + '/usuarios/'+ s.id +'?c=True')
                if not r.ok:
                    continue

                user = r.json()['usuario']
                fullName = user["nombre"] + " " + user["apellido"]

                try:
                    # datos a actualizar
                    datos = {}

                    datos["name"] = {"familyName": user["apellido"], "givenName": user["nombre"], "fullName": fullName}

                    r = service.users().update(userKey=userGoogle,body=datos).execute()
                    ds = cls._crearLog(r)
                    session.add(ds)
                    session.commit()

                    # actualizar alias
                    r = service.users().aliases().list(userKey=userGoogle).execute()
                    aliases = [a['alias'] for a in r.get('aliases', [])]
                    for e in s.emails.split(","):
                        if e not in aliases:
                            r = service.users().aliases().insert(userKey=userGoogle,body={"alias":e}).execute()
                            ds = cls._crearLog(r)
                            session.add(ds)
                            session.commit()

                    s.usuario_actualizado = fecha
                    s.actualizado = fecha
                    if s.usuario_creado is None:
                        s.usuario_creado = fecha

                    session.commit()

                    actualizados.append(datos)

                except errors.HttpError as err:
                    ds = cls._crearLog(err)
                    session.add(ds)
                    session.commit()
                    logging.exception(err)

                    s.error = s.error + 1
                    session.commit()

                    try:
                        # crear usuario
                        datos = {}
                        datos["aliases"] = s.emails.split(",")
                        datos["changePasswordAtNextLogin"] = False
                        datos["primaryEmail"] = userGoogle
                        datos["emails"] = [{'address': userGoogle, 'primary': True, 'type': 'work'}]

                        datos["name"] = {"givenName": user["nombre"], "fullName": fullName, "familyName": user["apellido"]}
                        datos["password"] = s.clave
                        datos["externalIds"] = [{'type': 'custom', 'value': s.id}]

                        r = service.users().insert(body=datos).execute()

                        ds = cls._crearLog(r)
                        session.add(ds)

                        # crear alias
                        for e in s.emails.split(","):
                            print("Correo a agregar enviar como:{}".format(e))
                            r = service.users().aliases().insert(userKey=userGoogle,body={"alias":e}).execute()
                            ds = cls._crearLog(r)
                            session.add(ds)

                        s.usuario_creado = fecha
                        s.usuario_actualizado = fecha

                        '''
                        # agregar los correos a enviar como
                        print("Esperar 2 segundos para que se cree el usuario")
                        time.sleep(2)
                        for e in s.emails.split(","):
                            cls.agregarAliasEnviarComo(fullName, e, userGoogle)
                        '''
                        session.commit()

                        creados.append(datos)

                    except Exception as err2:
                        ds = cls._crearLog(err2)
                        session.add(ds)
                        session.commit()
                        logging.exception(err2)

                        s.error = s.error + 1
                        session.commit()


            return {'creados':creados, 'actualizados':actualizados}

        finally:
            session.close()

    @classmethod
    def agregarEnviarComo(cls, id):
        session = Session()
        try:
            s = session.query(Sincronizacion).filter(Sincronizacion.id == id).one()
            if s is None:
                return False

            userGoogle = s.dni + "@econo.unlp.edu.ar"
            user = requests.get(cls.sileg_url + '/usuarios/'+ s.id +'?c=True').json()
            fullName = user["nombre"] + " " + user["apellido"]
            for e in s.emails.split(","):
                cls.agregarAliasEnviarComo(fullName, e, userGoogle)
            return True
        finally:
            session.close()

    @classmethod
    def agregarAliasEnviarComo(cls, name, email, userKeyG):
        alias = {
            'displayName': name,
            'replyToAddress': email,
            'sendAsEmail': email,
            'treatAsAlias': True,
            'isPrimary': False,
            'isDefault': True
        }
        print("enviar como:{}".format(name))
        print("alias:{}".format(alias))
        session = Session()
        try:

            try:
                gmail = GAuthApis.getServiceGmail(userKeyG)

                r = gmail.users().settings().sendAs().list(userId='me').execute()
                aliases = [ a['sendAsEmail'] for a in r['sendAs'] ]
                print('alias encontrados : {} '.format(aliases))


                if alias['sendAsEmail'] not in aliases:
                    print('creando alias')
                    r = gmail.users().settings().sendAs().create(userId='me', body=alias).execute()
                    ds = cls._crearLog(r)
                    session.add(ds)
                    session.commit()

            except Exception as e:
                print(e)

        finally:
            session.close()
