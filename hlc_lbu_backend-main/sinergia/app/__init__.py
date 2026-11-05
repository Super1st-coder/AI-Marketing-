from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_redis.client import FlaskRedis
from flask_jwt_extended.jwt_manager import JWTManager
from flask_babel import Babel, get_locale
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_cors import CORS
from flask_alembic import Alembic
from flask_pymongo import PyMongo
from celery import Celery, Task

import logging
from logging.handlers import RotatingFileHandler

db = SQLAlchemy()
redis_client = FlaskRedis(strict=True)
jwt = JWTManager()
babel = Babel()
alembic = Alembic() 
mongodb = PyMongo()

def create_app(config_type='dev'):
    from config import config

    app = Flask(__name__)

    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    app.config.from_object(config[config_type])

    app.config.from_mapping(
        CELERY=dict(
            broker_url = app.config['CELERY_BROKER_URL'],
            result_backend = app.config['CELERY_RESULT_BACKEND'],
            task_ignore_result = app.config['CELERY_TASK_IGNORE_RESULT'],
            imports = app.config['CELERY_IMPORTS'],
        ),
    )

    db.init_app(app)

    redis_client.init_app(app)

    jwt.init_app(app)

    babel.init_app(app)

    alembic.init_app(app)

    mongodb.init_app(app)

    celery_init_app(app)
      
    handler = RotatingFileHandler('sinergia.log', maxBytes=10000, backupCount=1)
    handler.setLevel(logging.DEBUG)
    app.logger.addHandler(handler)

    from .v1 import v1_blueprint
    from .v2 import v2_blueprint
    app.register_blueprint(v1_blueprint, url_prefix='/api/v1')
    app.register_blueprint(v2_blueprint, url_prefix='/api/v2')

    CORS(app, resources={r'/*': {'origins': '*'}})        

    @app.route('/health')
    def health_check():
        from sqlalchemy import text
        import os
        import requests
        
        services_status = {
            "postgres": "checking...",
            "redis": "checking...",
            "mongodb": "checking...",
            "strapi": "checking...",
            "sendgrid": "checking...",
            "abyssale": "checking...",
            "facebook": "checking...",
            "fury": "checking..."
        }
        
        is_healthy = True
        critical_errors = []
        
        # 1. Check Postgres (CRITICAL)
        try:
            db.session.execute(text('SELECT 1'))
            services_status["postgres"] = "ok"
        except Exception as e:
            services_status["postgres"] = f"error: {str(e)}"
            critical_errors.append(f"Postgres: {str(e)}")
            is_healthy = False
            
        # 2. Check Redis (CRITICAL)
        try:
            redis_client.ping()
            services_status["redis"] = "ok"
        except Exception as e:
            services_status["redis"] = f"error: {str(e)}"
            critical_errors.append(f"Redis: {str(e)}")
            is_healthy = False
            
        # 3. Check MongoDB (CRITICAL)
        try:
            mongodb.db.command('ping')
            services_status["mongodb"] = "ok"
        except Exception as e:
            services_status["mongodb"] = f"error: {str(e)}"
            critical_errors.append(f"MongoDB: {str(e)}")
            is_healthy = False
            
        # 4. Check Strapi (CRITICAL)
        try:
            from app.tools.strapi import StrapiClient
            strapi = StrapiClient()
            strapi_resp = strapi.get('accounts', params={'pagination[limit]': 1})
            if isinstance(strapi_resp, dict) and 'error' in strapi_resp:
                raise Exception(f"Strapi Error: {strapi_resp['error']}")
            services_status["strapi"] = "ok"
        except Exception as e:
            services_status["strapi"] = f"error: {str(e)}"
            critical_errors.append(f"Strapi: {str(e)}")
            is_healthy = False
            
        # 5. Check SendGrid API (NON-CRITICAL)
        try:
            from sendgrid import SendGridAPIClient
            sendgrid_key = app.config.get('SENDGRID_API_KEY')
            if not sendgrid_key or sendgrid_key == 'dummy':
                services_status["sendgrid"] = "dummy_key"
            else:
                sg = SendGridAPIClient(sendgrid_key)
                resp = sg.client.scopes.get()
                if resp.status_code not in (200, 201, 202):
                    raise Exception(f"SendGrid returned status code {resp.status_code}")
                services_status["sendgrid"] = "ok"
        except Exception as e:
            services_status["sendgrid"] = f"error: {str(e)}"
            
        # 6. Check Abyssale API (NON-CRITICAL)
        try:
            from app.tools.abyssale import AbyssaleClient
            abyssale = AbyssaleClient()
            if not abyssale.token or abyssale.token == 'dummy':
                services_status["abyssale"] = "dummy_token"
            else:
                resp = abyssale.get('templates', params={'limit': 1})
                if isinstance(resp, dict) and 'error' in resp:
                    raise Exception(f"Abyssale Error: {resp['error']}")
                services_status["abyssale"] = "ok"
        except Exception as e:
            services_status["abyssale"] = f"error: {str(e)}"
            
        # 7. Check Facebook Graph API (NON-CRITICAL)
        try:
            fb_client_id = os.getenv("FACEBOOK_CLIENT_ID")
            fb_graph_api_base = os.getenv("FACEBOOK_GRAPH_API_BASE", "https://graph.facebook.com")
            if not fb_client_id or fb_client_id == "dummy_fb_client_id":
                services_status["facebook"] = "dummy_config"
            else:
                resp = requests.get(fb_graph_api_base, timeout=3.0)
                if resp.status_code not in (200, 400):
                    raise Exception(f"Meta Graph API returned status code {resp.status_code}")
                services_status["facebook"] = "ok"
        except Exception as e:
            services_status["facebook"] = f"error: {str(e)}"
            
        # 8. Check Fury API (NON-CRITICAL)
        try:
            fury_url = app.config.get('FURY_URL')
            fury_api_key = app.config.get('FURY_SERVICE_API_KEY')
            if not fury_url or fury_url == 'http://dummy':
                services_status["fury"] = "dummy_url"
            else:
                headers = {}
                if fury_api_key:
                    headers["X-Internal-API-Key"] = fury_api_key
                resp = requests.get(f"{fury_url}/api/v2/health", headers=headers, timeout=3.0)
                if resp.status_code != 200:
                    raise Exception(f"Fury status code {resp.status_code}: {resp.text}")
                
                # Unpack and merge Fury's internal services status (e.g. openai, gemini)
                fury_data = resp.json()
                services_status["fury"] = "ok"
                fury_services = fury_data.get("services", {})
                for key, val in fury_services.items():
                    services_status[f"fury_{key}"] = val
        except Exception as e:
            services_status["fury"] = f"error: {str(e)}"
            
        if is_healthy:
            return {
                "status": "UP",
                "services": services_status
            }, 200
        else:
            app.logger.error(f"Healthcheck failed. Critical errors: {critical_errors}")
            return {
                "status": "DOWN",
                "errors": critical_errors,
                "services": services_status
            }, 503

    return app

def celery_init_app(app: Flask) -> Celery:
    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask)
    celery_app.config_from_object(app.config['CELERY'])
    celery_app.set_default()
    app.extensions["celery"] = celery_app
    return celery_app
