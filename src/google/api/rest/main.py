import logging
logging.getLogger().setLevel(logging.INFO)
import sys
from flask import Flask, abort, make_response, jsonify, url_for, request, json
from google.model import GoogleModel
from flask_jsontools import jsonapi

from rest_utils import register_encoder

app = Flask(__name__)
register_encoder(app)

@app.route('/google/api/v1.0/actualizar_usuarios/', methods=['OPTIONS'])
@app.route('/google/api/v1.0/actualizar_usuarios/<uid>', methods=['OPTIONS'])
@app.route('/google/api/v1.0/sincronizar_claves/', methods=['OPTIONS'])
@app.route('/google/api/v1.0/sincronizar_usuarios/', methods=['OPTIONS'])
@app.route('/google/api/v1.0/enviar_como/<uid>', methods=['OPTIONS'])
@app.route('/google/api/v1.0/google_usuario/<uid>', methods=['OPTIONS'])
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


# actualiza las bases de usuarios con la interna del sistema, dispara toda la sincronizacion
@app.route('/google/api/v1.0/google_usuario/<uid>', methods=['GET'])
@jsonapi
def googleUsuario(uid):
    GoogleModel.actualizarUsuarios(uid)
    GoogleModel.sincronizarUsuarios()
    GoogleModel.sincronizarClaves()

# actualiza las bases de usuarios con la interna del sistema
@app.route('/google/api/v1.0/actualizar_usuarios/', methods=['GET'], defaults={'uid':None})
@app.route('/google/api/v1.0/actualizar_usuarios/<uid>', methods=['GET'])
@jsonapi
def actualizarUsuario(uid):
    ''' toma de la base de usuarios los datos y lo sincroniza internamente con la base del sistema de google '''
    return GoogleModel.actualizarUsuarios(uid)



# sincroniza las claves pendientes con google
@app.route('/google/api/v1.0/sincronizar_claves/', methods=['GET'])
@jsonapi
def sincronizarClaves():
    return GoogleModel.sincronizarClaves()


# actualiza los usuarios pendientes con Google, si no existen los crea
@app.route('/google/api/v1.0/sincronizar/', methods=['GET'])
@jsonapi
def sincronizarUsuarios():
    return GoogleModel.sincronizarUsuarios()

# agrega los e-mails del id pasado como parametro como alias en gmail (enviarComo)
@app.route('/google/api/v1.0/enviar_como/<uid>', methods=['GET'])
@jsonapi
def enviarComo(uid):
    return GoogleModel.agregarEnviarComo(uid)


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
    app.run(host='0.0.0.0', port=5001, debug=True)

if __name__ == '__main__':
    main()
