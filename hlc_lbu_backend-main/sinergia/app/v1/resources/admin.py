from flask import request
from flask_restplus import Resource, fields
from app.v1 import v1_api
from flask_jwt_extended.view_decorators import jwt_required

from app.v1.resources.base import ProxySecureResource, secureHeader, queryParams, publicHeader
from app.v1.use_cases.admin import GetAdminMemberListUseCase,CreateAdminMemberUseCase,GetRolListUseCase,\
    SaveRolUseCase, UpdateAdminMemberUseCase, SendInviteAdminMemberUseCase,\
    MemberFinishRegisterUseCase,GetRoleUseCase, DropAdminMemberUseCase, GetAdminMemberByTypeUseCase,\
    DeleteAdminMemberByTypeUseCase, ReactivateAdminMemberByTypeUseCase
from app.v1.resources.entities import UpdateEmpresaStruct
from app.v1.repository.base import N8NClient
from app.tools.permissions import check_access
from app.v1.models.constant import ROLE_HILUCA_ADMIN, ROLE_SUPER_ADMIN, REGULAR_USER, ORGANIZATION_USER,\
    FUNCTION_ADMIN_ORG, FUNCTION_ADMIN_USER, FUNCTION_ADMIN_ROLES, ACTION_CREATE, ACTION_UPDATE, ACTION_READ, ACTION_DELETE

admin_ns = v1_api.namespace('admin', description='Admin Services')

RolStruct = v1_api.model('RolStruct', { 
    'id' : fields.Integer(), 
    'name' : fields.String(), 
})

GetRolStruct = v1_api.model('GetRolStruct', { 
    'id' : fields.Integer(), 
    'name' : fields.String(),
    'icon' : fields.String(),
    'status' : fields.String(),
})

UpdateRolStruct = v1_api.model('UpdateRolStruct', { 
    'name': fields.String(),
    # 'privileges' : fields.List(fields.String()), 
}) 

ExtraInfoUserStruct = v1_api.model('ExtraInfoUserStruct', { 
    #'id_number': fields.String(attribute='id_number'),
    'first_name': fields.String(attribute='first_name'),
    'last_name': fields.String(attribute='last_name'),
    'fullname': fields.String(attribute='fullname'),
    #'email': fields.String(attribute='email'),
    #'gender': fields.String(attribute='gender'),
    #'address': fields.String(attribute='address'),
    #'phone_number': fields.String(attribute='phone_number'),
    # #Datos Adicionales Creados para RRHH
    #'empresa': fields.Nested(EmpresaStruct,attribute='empresa'),
}) 

AdminUserStruct = v1_api.model('AdminUserStruct', { 
    'id': fields.String(attribute='id'),
    'account': fields.String(attribute='name'),
    'status': fields.String(attribute='status'),
    'roles' : fields.Nested(RolStruct,attribute='roles'),
    'extra_info': fields.Nested(ExtraInfoUserStruct,attribute='person_extension'),
}) 

UpdateExtraInfoUserStruct = v1_api.model('UpdateExtraInfoUserStruct', { 
    'id_number': fields.String(),
    'first_name': fields.String(),
    'last_name': fields.String(),
    'fullname': fields.String(),
    'email': fields.String(),
    'gender': fields.String(),
    'address': fields.String(),
    'phone_number': fields.String(),
    #Informacion Adicional Asociado al Usuario
    'empresa': fields.Nested(UpdateEmpresaStruct),
}) 

UpdateAdminUserStruct = v1_api.model('UpdateAdminUserStruct', { 
    'email': fields.String(),
    'first_name': fields.String(),
    'last_name': fields.String(),
    'roles' : fields.List(fields.Integer()), #Listado de Ids de Roles
}) 

CreateAdminUserStruct = v1_api.model('CreateAdminUserStruct', { 
    'email': fields.String(),
    'first_name': fields.String(),
    'last_name': fields.String(),
    'roles' : fields.List(fields.Integer()), #Listado de Ids de Roles
}) 


GetAdminUserListStruct = v1_api.model('GetAdminUserListStruct', { 
    'ok' : fields.Integer(description='Ok Result'), 
    'count' : fields.Integer(description='Count Row'), 
    'total' : fields.Integer(description='Total Row'), 
    'data' : fields.Nested(AdminUserStruct,attribute='data')
}) 


GetOneAdminUserStruct = v1_api.model('GetOneAdminUserStruct', { 
    'ok' : fields.Integer(description='Ok Result'), 
    'data' : fields.Nested(AdminUserStruct,attribute='data')
}) 

AdminUserSendInviteStruct = v1_api.model('AdminUserSendInviteStruct', { 
    'email': fields.String()
}) 

AdminUserFinishRegister = v1_api.model('AdminUserFinishRegister', {
    'email': fields.String(required=True, description='Email'),
    'confirmation_code': fields.String(required=True, description='Confirmation Key'),
    'password': fields.String(required=True, description='Password'),
    'confirm_password': fields.String(required=True, description='Confirm Password')
})

GetRolListStruct = v1_api.model('GetRolListStruct', { 
    'ok' : fields.Integer(description='Ok Result'), 
    'count' : fields.Integer(description='Count Row'), 
    'total' : fields.Integer(description='Total Row'), 
    'data' : fields.Nested(GetRolStruct,attribute='data')
}) 

ActionStruct = v1_api.model('ActionStruct', { 
    'id': fields.String(), 
    'name': fields.String()
})

FunctionStruct = v1_api.model('FunctionStruct', { 
    'id': fields.Integer(), 
    'name': fields.String(),
    'long_name': fields.String(),
    'status': fields.String(),
    'actions': fields.Nested(ActionStruct),
})

RoleStruct = v1_api.model('ARoleStruct', { 
    'id': fields.Integer(), 
    'name': fields.String(),
    'icon': fields.String(),
    'status': fields.String(),
    'functions': fields.Nested(FunctionStruct),
})

GetRoleStruct = v1_api.model('GetRoleStruct', { 
    'ok' : fields.Integer(description='Ok Result'), 
    'data' : fields.Nested(RoleStruct,attribute='data')
}) 

def create_user(credentials, payload, user_type):
    user = CreateAdminMemberUseCase().execute(credentials, payload, user_type)
        
    n8nClient = N8NClient(credentials=credentials)
    n8n_payload = {'email': user.name, 
                    'name': user.person_extension.fullname,
                    'type': 'org' if user_type == ORGANIZATION_USER else 'user'}
    
    try:
        response = n8nClient.executePost('/webhook/admin/account',n8n_payload,True)
    except Exception as e:
        # Eliminar usuario
        DropAdminMemberUseCase().execute(credentials,{'username': user.name})
        raise e
    
    return user

def update_user(credentials, payload, user_type = REGULAR_USER):
    payload['user_type'] = user_type
    user = UpdateAdminMemberUseCase().execute(credentials,payload)

    # Actualizar usuario en N8N
    n8nClient = N8NClient(credentials=credentials)
    n8n_payload = {'email': user.name, 'name': user.person_extension.fullname}
    response = n8nClient.executePut('/webhook/admin/account',n8n_payload,True)

    return user

def _get_external_users(credentials, user_type = REGULAR_USER):
    end_point = '/webhook/admin/user_accounts'
    if user_type == ORGANIZATION_USER:
        end_point = '/webhook/admin/org_accounts'

    n8nClient = N8NClient(credentials=credentials)    
    try:
        response = n8nClient.executeGet(end_point)
        if 'ok' in response and response['ok'] == 1:
            return response['data']['users']
        else:
            return None
    except Exception as e:
        return None

def get_users(credentials, request_args, user_type = REGULAR_USER):
    user_accounts = _get_external_users(credentials, user_type) 
    if not user_accounts:
        return { 'ok': 1, 'count': 0, 'total':  0  ,'data' : []} 
        
    str_user_accounts = str(user_accounts).replace('[', '(').replace(']', ')')

    query_params = {}
    request_payload =  {}        
    if 'filter' in  request_args and request_args['filter']:
        filter = eval(request_args['filter'])
        request_payload = filter
        request_payload['user_type'] = user_type
        request_payload['user_accounts'] = str_user_accounts
        query_params['filter'] = request_payload
    else:
        query_params['filter'] = {'user_type': user_type, 'user_accounts': str_user_accounts}

    if 'order' in  request_args and request_args['order']:
        order = eval(request_args['order'])
        query_params['order'] = order
    
    if 'range' in  request_args and request_args['range']:
        range = eval(request_args['range'])
        query_params['range'] = range
    
    data = GetAdminMemberListUseCase().execute(credentials,query_params)
    data['ok']= 1

    return data

def get_user(credentials, username, user_type = REGULAR_USER):
    query_params = {'username': username, 'user_type': user_type}
    data = GetAdminMemberByTypeUseCase().execute(credentials,query_params)
    return data

def delete_user(credentials, username, user_type = REGULAR_USER):
    query_params = {'username': username, 'user_type': user_type}
    data = DeleteAdminMemberByTypeUseCase().execute(credentials,query_params)
    return data

def reactivate_user(credentials, username, user_type = REGULAR_USER):
    query_params = {'username': username, 'user_type': user_type}
    data = ReactivateAdminMemberByTypeUseCase().execute(credentials,query_params)
    return data

@admin_ns.route('/organization')
@v1_api.expect(secureHeader)
class AdminOrgResource(ProxySecureResource): 
    
    @admin_ns.doc('Create Organization')
    @v1_api.expect(CreateAdminUserStruct)    
    @jwt_required    
    @v1_api.marshal_with(GetOneAdminUserStruct) 
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_ADMIN_ORG, ACTION_CREATE)
    def post(self):
        security_credentials = self.checkCredentials()
        payload = request.json
        user = create_user(security_credentials, payload, ORGANIZATION_USER)
        return  {'ok': 1, 'data': user}, 200
    

    @admin_ns.doc('Update Organization')
    @v1_api.expect(UpdateAdminUserStruct)    
    @jwt_required    
    @v1_api.marshal_with(GetOneAdminUserStruct) 
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_ADMIN_ORG, ACTION_UPDATE)
    def put(self):
        security_credentials = self.checkCredentials()
        payload = request.json
        user = update_user(security_credentials, payload, ORGANIZATION_USER)
        return  {'ok': 1, 'data': user}, 200    
    

    @admin_ns.doc('Get Organizations')
    @v1_api.expect(queryParams)    
    @jwt_required
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_ADMIN_ORG, ACTION_READ)
    @v1_api.marshal_with(GetAdminUserListStruct) 
    def get(self):
        security_credentials = self.checkCredentials()
        data = get_users(security_credentials, request.args, ORGANIZATION_USER)
        return  data , 200
    

@admin_ns.route('/organization/<username>')
@admin_ns.param('username', 'Nombre de Usuario')
@v1_api.expect(secureHeader)
class OneAdminOrganizationResource(ProxySecureResource):
    
    @admin_ns.doc('Get Organization')
    @v1_api.marshal_with(GetOneAdminUserStruct) 
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_ADMIN_ORG, ACTION_READ)
    def get(self,username):
        security_credentials = self.checkCredentials() 
        data = get_user(security_credentials, username, ORGANIZATION_USER)
        return  {'ok' : 1, 'data': data}, 200

    @admin_ns.doc('Remove Organization')
    @v1_api.marshal_with(GetOneAdminUserStruct) 
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_ADMIN_ORG, ACTION_DELETE)
    def delete(self,username):
        security_credentials = self.checkCredentials()
        data = delete_user(security_credentials, username, ORGANIZATION_USER)
        return  {'ok' : 1, 'data': data}, 200
    
    @admin_ns.doc('Reactivate Organization')
    @v1_api.marshal_with(GetOneAdminUserStruct) 
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_ADMIN_ORG, ACTION_UPDATE)
    def put(self,username):
        security_credentials = self.checkCredentials()
        data = reactivate_user(security_credentials, username, ORGANIZATION_USER)
        return  {'ok' : 1, 'data': data}, 200


@admin_ns.route('/organization/invite')
@v1_api.expect(secureHeader)
class AdminOrganizationInviteResource(ProxySecureResource): 

    @admin_ns.doc('Send Organization Invite')
    @v1_api.expect(AdminUserSendInviteStruct)    
    @jwt_required
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_ADMIN_ORG, ACTION_CREATE)
    def post(self):
        security_credentials = self.checkCredentials()
        payload = request.json      
        payload['user_type'] = ORGANIZATION_USER
        SendInviteAdminMemberUseCase().execute(security_credentials,payload)      
        return  {'ok': 1}, 200
    

@admin_ns.route('/member')
@v1_api.expect(secureHeader)
class AdminMemberResource(ProxySecureResource): 

    @admin_ns.doc('Get Members')
    @v1_api.expect(queryParams)    
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN, ROLE_SUPER_ADMIN], FUNCTION_ADMIN_USER, ACTION_READ)
    @v1_api.marshal_with(GetAdminUserListStruct) 
    def get(self):
        security_credentials = self.checkCredentials()
        data = get_users(security_credentials, request.args, REGULAR_USER)
        return  data , 200

    @admin_ns.doc('Create Member')
    @v1_api.expect(CreateAdminUserStruct)    
    @jwt_required
    @check_access([ROLE_HILUCA_ADMIN, ROLE_SUPER_ADMIN], FUNCTION_ADMIN_USER, ACTION_CREATE)
    @v1_api.marshal_with(GetOneAdminUserStruct) 
    def post(self):
        security_credentials = self.checkCredentials()
        payload = request.json   
        user = create_user(security_credentials, payload, REGULAR_USER)
        return  {'ok': 1, 'data': user}, 200

    @admin_ns.doc('Update Member')
    @v1_api.expect(UpdateAdminUserStruct)    
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN, ROLE_SUPER_ADMIN], FUNCTION_ADMIN_USER, ACTION_UPDATE)
    @v1_api.marshal_with(GetOneAdminUserStruct) 
    def put(self):
        security_credentials = self.checkCredentials()
        payload = request.json        
        user = update_user(security_credentials, payload)
        return  {'ok': 1, 'data': user}, 200

@admin_ns.route('/member/<username>')
@admin_ns.param('username', 'Nombre de Usuario')
@v1_api.expect(secureHeader)
class OneAdminMemberResource(ProxySecureResource):
    
    @admin_ns.doc('Get Member')
    @v1_api.marshal_with(GetOneAdminUserStruct) 
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN, ROLE_SUPER_ADMIN], FUNCTION_ADMIN_USER, ACTION_READ)
    def get(self,username):
        security_credentials = self.checkCredentials() 
        data = get_user(security_credentials, username, REGULAR_USER)
        return  {'ok' : 1, 'data': data}, 200

    @admin_ns.doc('Remove Member')
    @v1_api.marshal_with(GetOneAdminUserStruct) 
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN, ROLE_SUPER_ADMIN], FUNCTION_ADMIN_USER, ACTION_UPDATE)
    def delete(self,username):
        security_credentials = self.checkCredentials()
        data = delete_user(security_credentials, username, REGULAR_USER)        
        return  {'ok' : 1, 'data': data}, 200
    

@admin_ns.route('/member/invite')
@v1_api.expect(secureHeader)
class AdminMemberInviteResource(ProxySecureResource): 

    @admin_ns.doc('Send Member Invite')
    @v1_api.expect(AdminUserSendInviteStruct)    
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN, ROLE_SUPER_ADMIN], FUNCTION_ADMIN_USER, ACTION_CREATE)
    def post(self):
        security_credentials = self.checkCredentials()
        payload = request.json        
        SendInviteAdminMemberUseCase().execute(security_credentials,payload)      

        return  {'ok': 1}, 200


@admin_ns.route('/member/register/finish')
@v1_api.expect(publicHeader)
class AdminMemberFinishRegisterResource(Resource):
     
    @admin_ns.doc('Confirm Account')
    @admin_ns.expect(AdminUserFinishRegister)
    def put(self):
        payload = request.json
        data = MemberFinishRegisterUseCase().execute(payload)
        return  { 'ok': 1 } , 200


@admin_ns.route('/role')
@v1_api.expect(secureHeader)
class RolesResource(ProxySecureResource): 

    @admin_ns.doc('Get Roles')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN, ROLE_SUPER_ADMIN], FUNCTION_ADMIN_ROLES, ACTION_READ)
    @v1_api.marshal_with(GetRolListStruct) 
    def get(self):
        security_credentials = self.checkCredentials()
        query_params = {}
        data = GetRolListUseCase().execute(security_credentials,query_params)
        data['ok']= 1
        return  data , 200

    @admin_ns.doc('Save Role')
    @v1_api.expect(UpdateRolStruct)    
    @jwt_required   
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_ADMIN_ROLES, ACTION_CREATE) 
    def put(self):
        security_credentials = self.checkCredentials()
        payload = request.json        
        SaveRolUseCase().execute(security_credentials,payload)
        return  {'ok':1} , 200
    

@admin_ns.route('/role/<role_id>')
@v1_api.expect(secureHeader)
class RoleResource(ProxySecureResource): 

    @admin_ns.doc('Get a Role')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN, ROLE_SUPER_ADMIN], FUNCTION_ADMIN_ROLES, ACTION_READ)
    @v1_api.marshal_with(GetRoleStruct) 
    def get(self,role_id):
        security_credentials = self.checkCredentials()
        query_params = {'role_id': role_id}
        data = GetRoleUseCase().execute(security_credentials,query_params)
        data['ok']= 1
        return  data, 200