from app import create_app
import os
from flask_script import Manager
from app import db
from flask_jwt_extended.jwt_manager import JWTManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config_type = 'dev'
if 'CONFIG_TYPE' in os.environ:
    config_type = os.environ['CONFIG_TYPE']
    os.environ['CONFIG_TYPE'] = config_type

app = create_app(config_type)
manager = Manager(app)

@manager.command
def run(): 
    """Like a 'runserver' command but shorter, lol."""
    app.run('0.0.0.0',debug=True)


@manager.command
def run_tests():
    import unittest
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)


@manager.command
def debug_fix():
    """
    I have trouble with hitting breakpoints in lask-RESTful class methods.
    This method help me.
    """
    app.config['DEBUG'] = True
    app.config['PROPAGATE_EXCEPTIONS'] = True
    app.run(debug=True)


@manager.command
def db_init():
    with db.engine.connect() as conn:
        conn.execute("CREATE SCHEMA IF NOT EXISTS business;")
    db.create_all()


@manager.command
def seed_admin():
    """Crea un super admin con password temporal para pruebas."""
    from app.v1.models.security import User, PersonExtension, Rol
    from app.v1.models.constant import STATUS_ACTIVE, CONSOLE_USER, ROLE_SUPER_ADMIN, ROLE_HILUCA_ADMIN
    import datetime
    import secrets

    with app.app_context():
        temp_password = secrets.token_urlsafe(9)

        logger.info("Preparando usuario admin superadmin@hiluca.com...")
        user = User.query.filter_by(name='superadmin@hiluca.com').first()
        
        if user:
            logger.info("El usuario superadmin@hiluca.com ya existe. Actualizando password y forzando permisos correctos...")
        else:
            user = User()
            user.name = "superadmin@hiluca.com"
            user.status = STATUS_ACTIVE
            user.register_mode = 'B'
            user.type = CONSOLE_USER
            user.register_date = datetime.datetime.now()

        user.hash_password(temp_password)
        
        # Extension
        pe = PersonExtension.query.filter_by(email='superadmin@hiluca.com').first()
        if not pe:
            pe = PersonExtension(email='superadmin@hiluca.com', first_name='Super', last_name='Admin')
            db.session.add(pe)
        
        user.person_extension = pe
        
        # Roles - We must assign ROLE_HILUCA_ADMIN because endpoints explicitly check for it
        rol_hiluca = Rol.query.filter_by(id_name=ROLE_HILUCA_ADMIN).first()
        if not rol_hiluca:
            rol_hiluca = Rol(name="Hiluca Admin", id_name=ROLE_HILUCA_ADMIN, status=STATUS_ACTIVE)
            db.session.add(rol_hiluca)
            
        rol_super = Rol.query.filter_by(id_name=ROLE_SUPER_ADMIN).first()
        if not rol_super:
            rol_super = Rol(name="Super Admin", id_name=ROLE_SUPER_ADMIN, status=STATUS_ACTIVE)
            db.session.add(rol_super)
            
        user.roles = [rol_hiluca, rol_super]

        db.session.add(user)
        db.session.commit()
        
        # Sincronizar con Strapi
        from app.tools.strapi import StrapiClient
        strapi = StrapiClient()
        logger.info("Verificando cuenta superadmin@hiluca.com en Strapi...")
        try:
            resp = strapi.find_by_filters('accounts', {'email': 'superadmin@hiluca.com'})
            
            account_id = None
            import datetime
            now = datetime.datetime.now().isoformat()
            
            if not resp or not resp.get('data'):
                logger.info("Creando cuenta de superadmin (publicada) en Strapi...")
                account_resp = strapi.post('accounts', data={'data': {'name': 'Hiluca Super Admin', 'email': 'superadmin@hiluca.com', 'publishedAt': now}})
                if account_resp and account_resp.get('data'):
                    account_id = account_resp['data']['id']
            else:
                account_id = resp['data'][0]['id']
                
            if account_id:
                # Verificar si ya tiene marcas
                brands_resp = strapi.find_by_filters('brand-v2s', {'account_ref': account_id})
                if not brands_resp or not brands_resp.get('data'):
                    logger.info("Creando marca por defecto (Hiluca) en Strapi...")
                    brand_data = {
                        'name': 'Hiluca',
                        'account_ref': account_id,
                        'account_id': account_id,
                        'created_by_account': account_id,
                        'creation_method': 'MANUAL',
                        'website': 'https://hiluca.com',
                        'complete': False,
                        'identity': {
                            'about_us': {'value': '', 'source': []},
                            'mission': {'value': '', 'source': []},
                            'vision': {'value': '', 'source': []},
                            'values': {'value': [], 'source': []},
                            'tone_voice': {'value': [], 'source': []},
                            'complete': False
                        },
                        'logos': [],
                        'colors': [],
                        'typography': [],
                        'dos_donts': [],
                        'publishedAt': now
                    }
                    strapi.post('brand-v2s', data={'data': brand_data})
        except Exception as e:
            logger.error(f"Error sincronizando Strapi: {e}")
        
        logger.info("="*50)
        logger.info("¡Usuario superadmin@hiluca.com creado exitosamente!")
        logger.info(f"Password temporal: {temp_password}")
        logger.info("="*50)

@manager.command
def seed_roles():
    """Inicializa los roles, funciones y permisos basicos para el backend."""
    from app.v1.models.security import Rol, Function
    from app.v1.models.constant import (
        STATUS_ACTIVE, ROLE_HILUCA_ADMIN, ROLE_SUPER_ADMIN,
        FUNCTION_BRAND, FUNCTION_PRODUCT, FUNCTION_TARGET_CUSTOMER,
        FUNCTION_PROJECT, FUNCTION_UMBRELLA_CAMPAIGN, FUNCTION_CAMPAIGN_SETUP,
        FUNCTION_CAMPAIGN_CREATIVE, FUNCTION_FUNNEL_FLOW, FUNCTION_APPROVAL_PROCESS,
        FUNCTION_CAMPAIGN_LAUNCHPAD, FUNCTION_ADMIN_ORG, FUNCTION_ADMIN_USER, FUNCTION_ADMIN_ROLES,
        ACTION_CREATE, ACTION_UPDATE, ACTION_DELETE, ACTION_READ
    )
    from app import db

    logger.info("Iniciando seeder de roles y permisos...")

    functions_to_seed = [
        FUNCTION_BRAND, FUNCTION_PRODUCT, FUNCTION_TARGET_CUSTOMER,
        FUNCTION_PROJECT, FUNCTION_UMBRELLA_CAMPAIGN, FUNCTION_CAMPAIGN_SETUP,
        FUNCTION_CAMPAIGN_CREATIVE, FUNCTION_FUNNEL_FLOW, FUNCTION_APPROVAL_PROCESS,
        FUNCTION_CAMPAIGN_LAUNCHPAD, FUNCTION_ADMIN_ORG, FUNCTION_ADMIN_USER, FUNCTION_ADMIN_ROLES
    ]
    
    actions = [{"id": ACTION_CREATE}, {"id": ACTION_UPDATE}, {"id": ACTION_DELETE}, {"id": ACTION_READ}]

    with app.app_context():
        # Asegurar rol
        rol_hiluca = Rol.query.filter_by(id_name=ROLE_HILUCA_ADMIN).first()
        if not rol_hiluca:
            rol_hiluca = Rol(name="Hiluca Admin", id_name=ROLE_HILUCA_ADMIN, status=STATUS_ACTIVE)
            db.session.add(rol_hiluca)
            db.session.commit()

        # Insertar funciones
        db_functions = []
        for fn_name in functions_to_seed:
            fn = Function.query.filter_by(name=fn_name).first()
            if not fn:
                fn = Function(name=fn_name, long_name=fn_name.replace("_", " ").title(), status=STATUS_ACTIVE)
                db.session.add(fn)
            db_functions.append(fn)
        db.session.commit()

        logger.info("Asociando funciones a ROLE_HILUCA_ADMIN...")
        db.session.execute(f"DELETE FROM function_rol WHERE rol_id = {rol_hiluca.id}")
        
        for fn in db_functions:
            import json
            actions_json = json.dumps(actions).replace("'", "''")
            sql = f"INSERT INTO function_rol (rol_id, function_id, actions) VALUES ({rol_hiluca.id}, {fn.id}, '{actions_json}'::jsonb)"
            db.session.execute(sql)
            
        db.session.commit()
        logger.info("¡Roles y permisos insertados exitosamente!")

if __name__ == '__main__':
    manager.run()
