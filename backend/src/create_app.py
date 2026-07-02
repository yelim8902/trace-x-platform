import os
from flask import Flask
from flask_cors import CORS
from src.api.analysis import Analyzer
from src.extensions import db, migrate

def create_app(api_key: str) -> Flask:
    app = Flask(__name__)

    _configure_app(app)
    _configure_database(app)
    _initialize_extensions(app)
    _register_routes(app, api_key)
    _register_healthcheck(app)

    return app

def _configure_app(app: Flask):
    app.json.sort_keys = False
    app.json.ensure_ascii = False
    app.config['JSON_AS_ASCII'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret')
    CORS(app)

def _configure_database(app: Flask):
    db_host = os.getenv('DB_HOST')
    db_user = os.getenv('DB_USER')
    db_pass = os.getenv('DB_PASSWORD')
    db_name = os.getenv('DB_NAME')

    if db_host and db_user and db_name:
        app.config['SQLALCHEMY_DATABASE_URI'] = (
            f'mysql+pymysql://{db_user}:{db_pass}@{db_host}:3306/{db_name}'
        )
    else:
        # DB 환경변수 없으면 SQLite로 fallback (로컬 개발용)
        db_path = os.path.join(os.path.dirname(__file__), '..', 'local.db')
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.abspath(db_path)}'
        print('⚠️  DB 환경변수 없음 → SQLite(local.db) 사용')

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

def _initialize_extensions(app: Flask):
    db.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        try:
            from src.visualizing_data import models  # noqa: F401
            db.create_all()
        except Exception as e:
            print(f'⚠️  DB 초기화 실패 (집계 기능 비활성화): {e}')

def _register_routes(app: Flask, api_key: str):
    app.analyzer = Analyzer(api_key=api_key)

    from src.routes import dashboard, live_detection, analysis, reports
    from src.visualizing_data import bp as visualizing_bp

    app.register_blueprint(dashboard.bp)
    app.register_blueprint(live_detection.bp)
    app.register_blueprint(analysis.bp)
    app.register_blueprint(reports.bp)
    app.register_blueprint(visualizing_bp)

def _register_healthcheck(app: Flask):
    @app.route('/health', methods=['GET'])
    def health():
        return {
            'status': 'ok',
            'service': 'trace-x-backend'
        }, 200
