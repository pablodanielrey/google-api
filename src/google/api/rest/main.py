import logging
logging.getLogger().setLevel(logging.INFO)
import sys
import os
from flask import Flask, abort, make_response, jsonify, url_for, request, json
from flask_jsontools import jsonapi

from rest_utils import register_encoder

from google.model import obtener_session, GoogleModel

app = Flask(__name__)
register_encoder(app)

API_BASE = os.environ['API_BASE']


# actualiza las bases de usuarios con la interna del sistema, dispara toda la sincronizacion
@app.route(API_BASE + '/google_usuario/<uid>', methods=['GET'])
@jsonapi
def googleUsuario(uid):
    with obtener_session() as session:
        GoogleModel.actualizarUsuarios(session, uid)
        GoogleModel.sincronizarUsuarios(session)
        GoogleModel.sincronizarClaves(session)

# actualiza las bases de usuarios con la interna del sistema
@app.route(API_BASE + '/actualizar_usuarios/', methods=['GET'], defaults={'uid':None})
@app.route(API_BASE + '/actualizar_usuarios/<uid>', methods=['GET'])
#@app.route('/google/api_test/v1.0/actualizar_usuarios/', methods=['GET'], defaults={'uid':None})
#@app.route('/google/api_test/v1.0/actualizar_usuarios/<uid>', methods=['GET'])
@jsonapi
def actualizarUsuario(uid):
    with obtener_session() as session:
        return GoogleModel.actualizarUsuarios(session, uid)

# sincroniza las claves pendientes con google
@app.route(API_BASE + '/sincronizar_claves/', methods=['GET'])
#@app.route('/google/api_test/v1.0/sincronizar_claves/', methods=['GET'])
@jsonapi
def sincronizarClaves():
    with obtener_session() as session:
        return GoogleModel.sincronizarClaves(session)

# actualiza los usuarios pendientes con Google, si no existen los crea
@app.route(API_BASE + '/sincronizar/', methods=['GET'])
#@app.route('/google/api_test/v1.0/sincronizar/', methods=['GET'])
@jsonapi
def sincronizarUsuarios():
    with obtener_session() as session:
        return GoogleModel.sincronizarUsuarios(session)

# agrega los e-mails del id pasado como parametro como alias en gmail (enviarComo)
@app.route(API_BASE + '/enviar_como/<uid>', methods=['GET'])
@jsonapi
def enviarComo(uid):
    with obtener_session() as session:
        return GoogleModel.agregarEnviarComo(session, uid)



@app.route(API_BASE + '/actualizar_usuarios/', methods=['OPTIONS'])
@app.route(API_BASE + '/actualizar_usuarios/<uid>', methods=['OPTIONS'])
@app.route(API_BASE + '/sincronizar_claves/', methods=['OPTIONS'])
@app.route(API_BASE + '/sincronizar_usuarios/', methods=['OPTIONS'])
@app.route(API_BASE + '/enviar_como/<uid>', methods=['OPTIONS'])
@app.route(API_BASE + '/google_usuario/<uid>', methods=['OPTIONS'])
def options(uid=None):
    '''
        para autorizar el CORS
        https://developer.mozilla.org/en-US/docs/Web/HTTP/Access_control_CORS
    '''
    print(request.headers)
    o = request.headers.get('Origin')
    rm = request.headers.get('Access-Control-Request-Method')
    rh = request.headers.get('Access-Control-Request-Headers')

    r = make_response()
    r.headers[''] = 'PUT,POST,GET,HEAD,DELETE'
    r.headers['Access-Control-Allow-Methods'] = 'PUT,POST,GET,HEAD,DELETE'
    r.headers['Access-Control-Allow-Origin'] = '*'
    r.headers['Access-Control-Allow-Headers'] = rh
    r.headers['Access-Control-Max-Age'] = 1
    return r

@app.after_request
def add_header(r):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    """
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers['Cache-Control'] = 'public, max-age=0'

    r.headers['Access-Control-Allow-Origin'] = '*'
    return r

def main():
    app.run(host='0.0.0.0', port=5000, debug=True)

if __name__ == '__main__':
    main()
