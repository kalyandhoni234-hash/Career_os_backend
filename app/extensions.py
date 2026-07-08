from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from authlib.integrations.flask_client import OAuth
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
bcrypt = Bcrypt()
oauth = OAuth()
limiter = Limiter(key_func=get_remote_address)
