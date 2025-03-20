from flask import Flask
from flask_jwt_extended import JWTManager

from auth.views import auth_view
from helpers.db_config import initialize_db, Config
from gate_pass.views import gate_pass_view

app = Flask(__name__)

app.config.from_object(Config)


jwt = JWTManager(app)


initialize_db()

app.register_blueprint(auth_view, url_prefix="/api/auth")
app.register_blueprint(gate_pass_view, url_prefix="/api/gate_pass")

if __name__ == '__main__':
    app.run()
