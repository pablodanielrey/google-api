from google.model.GoogleAuthApi import GAuthApis
import base64
import email
from email.mime.text import MIMEText
from email.parser import Parser
from apiclient import errors
import os
import re, sys
import logging
import datetime

def crearMensaje(api, version, username, file, labelIds):
    scopes = ['https://www.googleapis.com/auth/gmail.insert','https://www.googleapis.com/auth/gmail.modify', 'https://mail.google.com/']
    service = GAuthApis.getService(version, api, scopes, username)

    headers = Parser().parse(file)
    urlsafe = base64.urlsafe_b64encode(headers.as_string().encode()).decode()

    num_tries = 0
    while num_tries < 5:
        try:
            msg = service.users().messages().insert(userId=username,internalDateSource='dateHeader',body={'raw': urlsafe, 'labelIds': labelIds}).execute()
            logging.info("Mail copiado")
            return msg
        except Exception as e:
            logging.info(e)
            num_tries += 1
    return None

def obtenerCorreos(api, version, username):
    scopes = ['https://www.googleapis.com/auth/gmail.readonly','https://www.googleapis.com/auth/gmail.modify', 'https://mail.google.com/']
    service = GAuthApis.getService(version, api, scopes, username)

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

def obtenerCorreo(api, version, username, mid):
    scopes = ['https://www.googleapis.com/auth/gmail.readonly','https://www.googleapis.com/auth/gmail.modify', 'https://mail.google.com/']
    service = GAuthApis.getService(version, api, scopes, username)

    correo  = service.users().messages().get(userId=username, id= mid).execute()

    return correo

def obtenerLabels(userId):
    scopes = ['https://mail.google.com/',
              'https://www.googleapis.com/auth/gmail.modify',
              'https://www.googleapis.com/auth/gmail.readonly',
              'https://www.googleapis.com/auth/gmail.labels',
              'https://www.googleapis.com/auth/gmail.metadata']

    service = GAuthApis.getService('v1', 'gmail', scopes, userId)
    try:
        response = service.users().labels().list(userId=userId).execute()
        labels = response['labels']
        return labels
    except errors.HttpError as error:
        logging.info('An error occurred: {}'.format(error))

def crearEtiqueta(userId, nombre):
    scopes = ['https://mail.google.com/',
              'https://www.googleapis.com/auth/gmail.modify',
              'https://www.googleapis.com/auth/gmail.labels']

    service = GAuthApis.getService('v1', 'gmail', scopes, userId)
    try:
        label = service.users().labels().create(userId=userId, body={'name':nombre}).execute()
        logging.info('se ha creado la etiqueta: {}'.format(label))
        return label
    except errors.HttpError as error:
        logging.info('An error occurred: {}'.format(error))

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

if __name__ == '__main__':
    version ='v1'
    api = 'gmail'
    username = sys.argv[1]
    maildir = sys.argv[2]
    directorioBase = maildir.split('/')[-1]


    logFile = '/var/log/migracion-{}-{}.log'.format(username,str(datetime.datetime.now()))
    logging.basicConfig(filename=logFile, filemode='w', level=logging.INFO)
    print('logueando info del proceso sobre : {}'.format(logFile))

    patron = re.compile('\..+')


    (base, dirs, files) = next(os.walk(maildir))

    omitir = ['.sent', '.enviados', '.borradores', '.draft','.trash', '.eliminados', '.papelera']
    omitir.extend(['sent', 'enviados', 'borradores', 'draft','trash', 'eliminados', 'papelera', 'tmp', 'cur', 'new'])

    labelsGoogle = obtenerLabels(username)
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
            if l not in etiquetasGoogle:
                logging.info('se va a crear la etiqueta: {}'.format(l))
                e = crearEtiqueta(username, l)
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

            if label.lower() in ["trash", "eliminados", "papelera"]:
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

    # copio los correos a google
    logging.info('copiando correos')
    for label in archivos.keys():
        files = archivos[label]
        for archivo in files["files"]:
            logging.info("archivo a copiar " + archivo)
            with open(archivo, 'r', encoding="latin-1") as file:
                labelId = files["labelId"]
                logging.info("Mail a copiar {} label: {}".format(archivo, labelId))
                crearMensaje(api, version, username, file, [labelId])
