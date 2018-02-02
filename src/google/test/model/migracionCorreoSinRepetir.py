
import base64
import email
from email.mime.text import MIMEText
from email.parser import Parser
from apiclient import errors
import os
import re, sys
import logging
import datetime
import time


import os

from apiclient import discovery, errors
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
from oauth2client.service_account import ServiceAccountCredentials
import httplib2

class GAuthApis:

    adminGoogle = os.environ['ADMIN_USER_GOOGLE']

    SCOPES = 'https://www.googleapis.com/auth/admin.directory.user'

    SCOPESGMAIL = [
        'https://mail.google.com/',
        'https://www.googleapis.com/auth/gmail.settings.sharing'
    ]

    """
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
              'https://www.googleapis.com/auth/drive']
    """

    @classmethod
    def getCredentials(cls, username, SCOPES=SCOPES):
        ''' genera las credenciales delegadas al usuario username '''
        home_dir = os.path.expanduser('~')
        credential_dir = os.path.join(home_dir, '.credentials')
        if not os.path.exists(credential_dir):
            os.makedirs(credential_dir)
        credential_path = os.path.join(credential_dir,'credentials.json')

        credentials = ServiceAccountCredentials.from_json_keyfile_name(credential_path, SCOPES)

        ''' uso una cuenta de admin del dominio para acceder a todas las apis '''
        admin_credentials = credentials.create_delegated(username)

        return admin_credentials

    @classmethod
    def getService(cls, version, api, scopes, username=adminGoogle):
        credentials = cls.getCredentials(username, scopes)
        http = credentials.authorize(httplib2.Http())
        service = discovery.build(api, version, http=http, cache_discovery=False)
        return service

    @classmethod
    def getServiceAdmin(cls, username=adminGoogle, version='directory_v1'):
        api='admin'
        return cls.getService(version, api, cls.SCOPES, username)


    @classmethod
    def getServiceGmail(cls, username=adminGoogle, version='v1'):
        api='gmail'
        return cls.getService(version, api, cls.SCOPESGMAIL, username)




def crearMensaje(service, api, version, username, file, labelIds, fileName):
    #scopes = ['https://www.googleapis.com/auth/gmail.insert','https://www.googleapis.com/auth/gmail.modify', 'https://mail.google.com/']
    #service = GAuthApis.getService(version, api, scopes, username)

    headers = Parser().parse(file)
    urlsafe = base64.urlsafe_b64encode(headers.as_string().encode()).decode()

    num_tries = 0
    while num_tries < 5:
        try:
            msg = service.users().messages().insert(userId=username,internalDateSource='dateHeader',body={'raw': urlsafe, 'labelIds': labelIds}).execute()
            logging.info("Mail copiado:{}".format(fileName))
            return msg
        except Exception as e:
            logging.exception(e)
            num_tries += 1
            time.sleep(num_tries * 60)
    return None

def obtenerCorreos(service, api, version, username):
    #scopes = ['https://www.googleapis.com/auth/gmail.readonly','https://www.googleapis.com/auth/gmail.modify', 'https://mail.google.com/']
    #service = GAuthApis.getService(version, api, scopes, username)

    respuesta = service.users().messages().list(userId=username).execute()
    ids = []
    if 'messages' in respuesta:
        ids.extend([m["id"] for m in respuesta["messages"]])

    while 'nextPageToken' in respuesta:
        page_token = respuesta['nextPageToken']
        respuesta = service.users().messages().list(userId=username, pageToken=page_token).execute()
        if 'messages' in respuesta:
            ids.extend([m["id"] for m in respuesta["messages"]])

    return ids

def obtenerCorreo(service, api, version, username, mid):
    #scopes = ['https://www.googleapis.com/auth/gmail.readonly','https://www.googleapis.com/auth/gmail.modify', 'https://mail.google.com/']
    #service = GAuthApis.getService(version, api, scopes, username)

    correo  = service.users().messages().get(userId=username, id= mid).execute()

    return correo

def obtenerLabels(service, userId):
    #scopes = ['https://mail.google.com/',
    #          'https://www.googleapis.com/auth/gmail.modify',
    #          'https://www.googleapis.com/auth/gmail.readonly',
    #          'https://www.googleapis.com/auth/gmail.labels',
    #          'https://www.googleapis.com/auth/gmail.metadata']

    #service = GAuthApis.getService('v1', 'gmail', scopes, userId)
    try:
        response = service.users().labels().list(userId=userId).execute()
        labels = response['labels']
        return labels
    except errors.HttpError as err:
        logging.info('An error occurred: {}'.format(err))

def crearEtiqueta(service, userId, nombre):
    #scopes = ['https://mail.google.com/',
    #          'https://www.googleapis.com/auth/gmail.modify',
    #          'https://www.googleapis.com/auth/gmail.labels']

    #service = GAuthApis.getService('v1', 'gmail', scopes, userId)
    try:
        label = service.users().labels().create(userId=userId, body={'name':nombre}).execute()
        logging.info('se ha creado la etiqueta: {}'.format(label))
        return label
    except errors.HttpError as err:
        logging.info('An error occurred: {}'.format(err))


def obtenerServicio(userId):
    scopes = ['https://mail.google.com/',
              'https://www.googleapis.com/auth/gmail.insert',
              'https://www.googleapis.com/auth/gmail.modify',
              'https://www.googleapis.com/auth/gmail.readonly',
              'https://www.googleapis.com/auth/gmail.labels',
              'https://www.googleapis.com/auth/gmail.metadata']

    service = GAuthApis.getService('v1', 'gmail', scopes, userId)
    return service

def parsearEtiqueta(label, directorioBase):
    label = label[1:] if label[0] == '/' else label
    if label == directorioBase:
        return "INBOX"
    elif label.lower() == "enviados" or label.lower() == "sent":
        return "SENT"
    elif label.lower() == "borradores" or label.lower() == "draft":
        return "DRAFT"
    else:
        return label

def parsearLog(archivo):
    correos = []
    with open(archivo, 'r') as file:
        for l in file:
            if "Mail a copiar" in l:
                msg = l.split(" ")[-3]
                correos.append(parsearCorreo(msg))
    return correos

# correo = 'Maildir/.Enviados/cur/1461263043.M420248P16836.correo,S=207444,W=210155:2,S'
def parsearCorreo(correo):
    array = correo.split("/")
    return array[-1].split(",")[0]


if __name__ == '__main__':
    version ='v1'
    api = 'gmail'
    username = sys.argv[1]
    maildir = sys.argv[2]
    fileLog = sys.argv[3]
    directorioBase = maildir.split('/')[-1]


    logFile = '/var/log/migracion-{}-{}.log'.format(username,str(datetime.datetime.now()))
    logging.basicConfig(filename=logFile, filemode='w', level=logging.INFO)
    print('logueando info del proceso sobre : {}'.format(logFile))

    service = obtenerServicio(username)

    patron = re.compile('\..+')

    (base, dirs, files) = next(os.walk(maildir))

    omitir = ['.sent', '.enviados', '.borradores', '.draft','.trash', '.eliminados']
    omitir.extend(['sent', 'enviados', 'borradores', 'draft','trash', 'eliminados', 'tmp', 'cur', 'new'])

    labelsGoogle = obtenerLabels(service, username)
    logging.info('etiquestas de google {}'.format(labelsGoogle))
    etiquetasGoogle = [l["name"] for l in labelsGoogle]
    etiquetasNuevas = []

    etiquetas = {}
    for l in labelsGoogle:
        etiquetas[l['name']] = l['id']

    # creo las etiquetas en google
    logging.info('creando carpetas')
    for d in dirs:
        if d.lower() not in omitir:
            l = d.replace(".","/")
            l = l[1:] if l[0] == '/' else l
            logging.info("Directorio:" + d)
            if l not in etiquetasGoogle:
                e = crearEtiqueta(service, username, l)
                etiquetasNuevas.append({'id': e['id'], 'name': e['name']})
                etiquetas[e['name']] = e['id']
            else:
                logging.info('la etiqueta {} ya existe'.format(l))

    logging.info("Etiquetas creadas: {}".format(etiquetasNuevas))

    # obtengo los correos a copiar en cada etiqueta
    logging.info('obteniendo correos a migrar')
    archivos = {}
    i = 0
    for (base, dirs, files) in os.walk(maildir):
        if base[-4:] in ['/cur','/new']:
            arr = base.split('/')
            label = arr[-2].replace(".","/")
            label = parsearEtiqueta(label, directorioBase)

            if label.lower() in ["trash", "eliminados"]:
                continue
            if label in archivos:
                e = archivos[label]
                correos = [base + '/' + f for f in files]
                e["files"].extend(correos)
                i += len(files)
            else:
                correos = [base + '/' + f for f in files]
                archivos[label] = {'label': label, 'files': correos, 'labelId': etiquetas[label]}
                i += len(files)

    logging.info('cantidad de correos a copiar: {}'.format(i))


    # obtengo los correos que ya se copiaron en el log
    correosLogs = parsearLog(fileLog)

    # copio los correos a google
    logging.info('copiando correos')
    for label in archivos.keys():
        files = archivos[label]
        for archivo in files["files"]:
            # verifico que no se encuentre en el log
            if parsearCorreo(archivo) in correosLogs:
                logging.info("El archivo {} se encuentra en el log, por ende no sera copiado".format(archivo))
                continue

            logging.info("archivo a copiar " + archivo)
            with open(archivo, 'r', encoding="latin-1") as file:
                labelId = files["labelId"]
                logging.info("Mail a copiar {} label: {}".format(archivo, labelId))
                crearMensaje(service, api, version, username, file, [labelId], archivo)
