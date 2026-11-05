from flask import request
from flask_restplus import Resource, fields
from app import redis_client
from app.v1 import v1_api
import datetime
from flask_jwt_extended.utils import create_access_token, create_refresh_token,\
    get_jti, get_raw_jwt, get_jwt_identity
from flask_jwt_extended.view_decorators import jwt_required,\
    jwt_refresh_token_required
from ..use_cases.security import AuthenticateUseCase
import json
import os
from ..repository.base import CacheRepository
from app.exceptions.base import ProxyCredentialsNotFound

from app.v1.use_cases.security import   MemberInitSignUpUseCase,\
    MemberFinishRegisterUseCase, UpdateMemberProfileUseCase, ChangePasswordMemberUseCase,\
    InitResetPasswordMemberUseCase,FinishResetPasswordMemberUseCase,\
    GetAnyMemberProfileUseCase, GetDetailedMemberProfileUseCase,\
    GetUserByNameUseCase, MemberUnsubscribeRegisterUseCase,\
    MemberResendConfirmationRegisterUseCase, MemberGetPermissionsUseCase

from app.v1.models.constant import STATUS_ACTIVE, STATUS_PENDING,STATUS_LOCKED,\
    STATUS_UNSUBSCRIBE, STATUS_INACTIVE, SUFFIX_PERMISSION


from app.v1.repository.base import N8NClient

member_ns = v1_api.namespace('member', description='Security Services')

mLogin = v1_api.model('Login', {
    'username': fields.String(required=True, description='User Name '),
    'password': fields.String(required=True, description='Password User'),
    'access_exp_time': fields.Integer(required=False, description='Access Time in seconds'),
    'refresh_exp_time': fields.Integer(required=False, description='Refresh Time in seconds')
})

mMemberInitRegister = v1_api.model('MemberInitRegister', {
    'email': fields.String(required=True, description='Email'),
    'first_name': fields.String(required=True, description='First Name'),
    'last_name': fields.String(required=True, description='Last Name'),
    # New fields in the registration process
    # 'phone_number': fields.String(required=False, description='Phone Number'),
    # 'gender': fields.String(required=False, description='Gender'),
    # 'birth_date': fields.String(required=False, description='Birth Date'),
    'password': fields.String(required=True, description='New Password')
})

# mMemberFinishRegister = v1_api.model('MemberFinishRegister', {
#     'phone_number': fields.String(required=True, description='Phone Number'),
#     'gender': fields.String(required=True, description='Gender'),
#     'secondary_email': fields.String(required=True, description='Secondary email'),
#     'birth_date': fields.String(required=True, description='Birth Date'),
#     'operation_key': fields.String(required=True, description='Operation Key of Operations'),
#     'password': fields.String(required=True, description='New Password')
# })

mMemberFinishRegister = v1_api.model('MemberFinishRegister', {
    'email': fields.String(required=True, description='Email'),
    'confirmation_code': fields.String(required=True, description='Confirmation Key'),
})

mMemberEmail = v1_api.model('MemberEmail', {
    'email': fields.String(required=True, description='Email')
})

mMemberFinishResetPassword = v1_api.model('MemberFinishResetPassword', {
    'email': fields.String(required=True, description='Email'),
    'confirmation_code': fields.String(required=True, description='Confirmation Key'),
    'new_password': fields.String(required=True, description='New Password')
})


mUserExtraInfo = v1_api.model('User Extra Info', { 
    'username': fields.String(description='Username'),
    'status': fields.String(description='Status') 
})

mLoginInfo = v1_api.model('Login Info', {
    'access_token': fields.String(description='Access Token '),
    'refresh_token': fields.String(description='Refresh Token'),
    'extra_info' : fields.Nested(mUserExtraInfo)
})

mResultLogin = v1_api.model('Result Login', { 
    'ok' : fields.Integer(description='Ok Result'), 
    'data' : fields.Nested(mLoginInfo)
}) 

mTokenPair = v1_api.model('TokenPair', {
    'extra_info': fields.Raw(),
    'access_token': fields.String(description='Access Token '),
    'refresh_token': fields.String(description='Refresh Token')
})

mResultTokens = v1_api.model('Result Token', { 
    'ok' : fields.Integer(description='Ok Result'), 
    'data' : fields.Nested(mTokenPair)
}) 

mRefreshToken = v1_api.model('RefreshToken', {
    'refresh_token': fields.String(required=True, description='Refresh Token')
}) 

mAccessToken = v1_api.model('AccessToken', {
    'access_token': fields.String(required=True, description='Access Token')
}) 

mMessage = v1_api.model('Message', { 
    'code': fields.String(description='Message Code'),
    'text': fields.String(description='Message Text') 
})

mResult = v1_api.model('Generic Result', { 
    'ok' : fields.Integer(description='Ok Result'), 
    'message' : fields.Nested(mMessage)
}) 

mChangePassword = v1_api.model('ChangePassword', {
    'old_password': fields.String(required=True, description='Old Password'),
    'new_password': fields.String(required=True, description='New Password'),
})

mMemberUnsubscribeRegister = v1_api.model('mMemberUnsubscribeRegister', {
    'email': fields.String(required=True, description='Email'),
    'confirmation_code': fields.String(required=True, description='Confirmation Key'),
})

# BankStruct = v1_api.model('BankStruct', { 
#     'id': fields.String(attribute='id'),
#     'name': fields.String(attribute='name'),
#     'account_number': fields.String(attribute='account_number'),
# }) 

UpdateProfileUserStruct = v1_api.model('UpdateProfileUserStruct', {
    'first_name': fields.String(required=True, description='First Name'),
    'last_name': fields.String(required=True, description='Last Name'),
    'phone_number': fields.String(required=True, description='Phone Number'),
    'gender': fields.String(required=True, description='Gender'),
    'secondary_email': fields.String(required=True, description='Secondary email'),
    'birth_date': fields.String(required=True, description='Birth Date'),
})


ProfileRolStruct = v1_api.model('ProfileRolStruct', { 
    'id' : fields.Integer(), 
    'name' : fields.String(), 
})


ProfileUserStruct = v1_api.model('ProfileUserStruct', { 
    'id': fields.String(attribute='id'),
    'id_number': fields.String(attribute='person_extension.id_number'),
    'first_name': fields.String(attribute='person_extension.first_name'),
    'last_name': fields.String(attribute='person_extension.last_name'),
    'fullname': fields.String(attribute='person_extension.fullname'),
    'email': fields.String(attribute='person_extension.email'),
    'gender': fields.String(attribute='person_extension.gender'),
    'address': fields.String(attribute='person_extension.address'),
    'phone_number': fields.String(attribute='person_extension.phone_number'),

    'roles' : fields.Nested(ProfileRolStruct,attribute='roles'),
    # 'bank' : fields.Nested(BankStruct,attribute='person_extension.bank')
}) 

GetProfileUserStruct = v1_api.model('GetProfileUserStruct', { 
    'ok' : fields.Integer(description='Ok Result'), 
    'data' : fields.Nested(ProfileUserStruct,attribute='data')
}) 

DateRangeStruct = v1_api.model('DateRangeStruct', { 
    'from': fields.String(description='From'),
    'to': fields.String(description='To') 
})

secureHeader = v1_api.parser()
secureHeader.add_argument('Authorization', type=str,location='headers',help='Bearer Access Token',required=True)
secureHeader.add_argument('Accept-Language', type=str,location='headers',help="en-US,en;q=0.5")

publicHeader = v1_api.parser()
publicHeader.add_argument('Accept-Language', type=str,location='headers',help="en-US,en;q=0.5")

queryParams = v1_api.parser()
queryParams.add_argument('filter',type=str,  help='{"stringParamName" : "stringParamValue","numericParamName" : numericParamValue}', location='args')
queryParams.add_argument('order',type=str, location='args', help='["field1","field2 ASC","field3 DESC"]')
queryParams.add_argument('range',type=str, location='args', help='[low,high]')

from werkzeug import FileStorage

uploadFilePublicHeader = v1_api.parser()
uploadFilePublicHeader.add_argument('Accept-Language', type=str,location='headers',help="en-US,en;q=0.5")
uploadFilePublicHeader.add_argument('file', location='files', type=FileStorage, required=True)

uploadFileSecureHeader = v1_api.parser()
uploadFileSecureHeader.add_argument('Authorization', type=str,location='headers',help='Bearer Access Token',required=True)
uploadFileSecureHeader.add_argument('Accept-Language', type=str,location='headers',help="en-US,en;q=0.5")
uploadFileSecureHeader.add_argument('file', location='files', type=FileStorage, required=True)

ACCESS_EXPIRES  = 300
REFRESH_EXPIRES = 43200 * 2

@member_ns.route('/login')
@v1_api.expect(publicHeader)
class MemberLoginResource(Resource):

    @member_ns.doc('Make Login in Application')
    @member_ns.expect(mLogin)
#     @member_ns.marshal_with(mResultLogin)
#     @member_ns.marshal_with(mResult, code=401,description='Error')
    def post(self):
        data = request.json

        username = data['username']
        password = data['password']
        FINAL_ACCESS_EXPIRES = ACCESS_EXPIRES
        FINAL_REFRESH_EXPIRES = REFRESH_EXPIRES

        sinergia_env = os.environ.get('SINERGIA_ENV', 'qas')

        # Solo en ambiente de desarrollo se pueden modificar los tiempos de expiración de los tokens desde el body del request, 
        # para facilitar las pruebas. 
        # Esto no se debe permitir en ambientes de producción o pre-producción.
        if sinergia_env == 'dev':
            access_time = data.get('access_exp_time')
            refresh_time = data.get('refresh_exp_time')

            if access_time and isinstance(access_time, int) and access_time > 0 and access_time < FINAL_ACCESS_EXPIRES:
                FINAL_ACCESS_EXPIRES = access_time

            if refresh_time and isinstance(refresh_time, int) and refresh_time > 0 and refresh_time < FINAL_REFRESH_EXPIRES:
                FINAL_REFRESH_EXPIRES = refresh_time
        
        securityElement = AuthenticateUseCase().execute(username, password)
        if securityElement == None:
            error =  { 'ok' : 0, 
                       'message' : { 
                           'code' : 'ESEC000',
                           'text': "Bad username or password"
                        } 
                      }
            return error, 401
        
        if securityElement.status in (STATUS_LOCKED,STATUS_PENDING) : 
            error =  { 'ok' : 0, 
                'message' : { 
                    'code' : 'ESEC000',
                    'text': "Locked User or Not Finished Register"
                } 
                }
            return error, 401
        
        if securityElement.status in (STATUS_UNSUBSCRIBE) : 
            error =  { 'ok' : 0, 
                'message' : { 
                    'code' : 'ESEC000',
                    'text': "Unsubscribed User"
                } 
                }
            return error, 401
        
        if securityElement.status in (STATUS_INACTIVE) : 
            error =  { 'ok' : 0, 
                'message' : { 
                    'code' : 'ESEC000',
                    'text': "Inactive User"
                } 
                }
            return error, 401

        access_token = create_access_token(identity=username,expires_delta=datetime.timedelta(seconds=FINAL_ACCESS_EXPIRES))
        refresh_token = create_refresh_token(identity=username,expires_delta=datetime.timedelta(seconds=FINAL_REFRESH_EXPIRES))
    
        # Store the tokens in redis with a status of not currently revoked. We
        # can use the `get_jti()` method to get the unique identifier string for
        # each token. We can also set an expires time on these tokens in redis,
        # so they will get automatically removed after they expire. We will set
        # everything to be automatically removed shortly after the token expires0
        access_jti = get_jti(encoded_token=access_token)
        refresh_jti = get_jti(encoded_token=refresh_token)
        
        
        payload = { "session_expired" : "false", "username" : username, "password": password, "id" : securityElement.id }
        user = GetUserByNameUseCase().execute(payload)

        payload['person_id'] = username
        payload['person_extension_id'] = user.person_extension_id

        redis_client.set(access_jti, json.dumps(payload), ex=int(FINAL_ACCESS_EXPIRES))
        redis_client.set(refresh_jti, json.dumps(payload), ex=int(FINAL_REFRESH_EXPIRES))

        userTokens = {'access_token' : access_jti,'refresh_token': refresh_jti}
        redis_client.set(username, json.dumps(userTokens), ex=int(FINAL_REFRESH_EXPIRES))

        # Buscar los permisos del usuario y guardarlos en redis
        permissions = MemberGetPermissionsUseCase().execute(username)
        redis_client.set(f"{username}{SUFFIX_PERMISSION}", json.dumps(permissions), ex=int(FINAL_ACCESS_EXPIRES))

        # Use create_access_token() and create_refresh_token() to create our
        # access and refresh tokens
        ret = { 'ok': 1,
            'data': {
                'extra_info' : {
                    'username' : username,
                    'status' : securityElement.status,
                    'full_name' : user.person_extension.fullname,
                    'permissions' : permissions
                },
                'access_token': access_token,
                'refresh_token': refresh_token
            }
        }
        return ret,200


@member_ns.route('/logout')
@v1_api.expect(secureHeader)
class MemberLogoutResource(Resource):

    @member_ns.doc('Make Logout Application')
    @member_ns.expect(mRefreshToken)
    @member_ns.marshal_with(mResult, code=200)
    @jwt_required    
    def post(self):
        data = request.json
        refresh_token = data['refresh_token']

        access_token_jti = get_raw_jwt()['jti']
        refresh_token_jti = get_jti(refresh_token)

        username = None

        if redis_client.get(access_token_jti):
            payload = redis_client.get(access_token_jti)    
            json_payload = json.loads(payload)
            json_payload["session_expired"] = 'true' 
            redis_client.set(access_token_jti, json.dumps(json_payload), ex=int(ACCESS_EXPIRES))
        else:
            redis_client.set(access_token_jti, json.dumps({"session_expired" : 'true'}), ex=int(ACCESS_EXPIRES))            

        if redis_client.get(refresh_token_jti):
            payload = redis_client.get(refresh_token_jti)
            json_payload = json.loads(payload)
            username = json_payload['username']
            json_payload["session_expired"] = 'true' 
            redis_client.set(refresh_token_jti, json.dumps(json_payload), ex=int(ACCESS_EXPIRES * 1.2))
        else:
            redis_client.set(refresh_token_jti, json.dumps({"session_expired" : 'true'}), ex=int(ACCESS_EXPIRES))      

        # Eliminar los permisos del usuario en redis
        if username:
            redis_client.delete(f"{username}{SUFFIX_PERMISSION}")

        return { 'ok' : 1, 
                'message' : { 
                    'code' : 'I001',
                    'text': 'OK'
                } 
                },200
    

@member_ns.route('/token/refresh')
@v1_api.expect(secureHeader)
class TokenRefreshResource(Resource):

    @member_ns.doc('Refresh Token')
    @member_ns.marshal_with(mResultTokens, code=200)
    @jwt_refresh_token_required
    def post(self):
        refresh_token_jti = get_raw_jwt()['jti']

        FINAL_ACCESS_EXPIRES = ACCESS_EXPIRES
        FINAL_REFRESH_EXPIRES = REFRESH_EXPIRES

        sinergia_env = os.environ.get('SINERGIA_ENV', 'qas')

        # Solo en ambiente de desarrollo se pueden modificar los tiempos de expiración de los tokens desde el body del request, 
        # para facilitar las pruebas. 
        # Esto no se debe permitir en ambientes de producción o pre-producción.
        if sinergia_env == 'dev' and request.json:
            data = request.json
            access_time = data.get('access_exp_time')
            refresh_time = data.get('refresh_exp_time')

            if access_time and isinstance(access_time, int) and access_time > 0 and access_time < FINAL_ACCESS_EXPIRES:
                FINAL_ACCESS_EXPIRES = access_time

            if refresh_time and isinstance(refresh_time, int) and refresh_time > 0 and refresh_time < FINAL_REFRESH_EXPIRES:
                FINAL_REFRESH_EXPIRES = refresh_time


        username = get_jwt_identity()
        access_token = create_access_token(identity=username,expires_delta=datetime.timedelta(seconds=FINAL_ACCESS_EXPIRES))
        access_jti = get_jti(encoded_token=access_token)

        cacheRepository = CacheRepository()
        payload = cacheRepository.getByKey(refresh_token_jti)

        user = GetUserByNameUseCase().execute(payload)
        if user.status == STATUS_ACTIVE:
            payload['person_id'] = username            
            payload['person_extension_id'] = user.person_extension_id
        else:           
            error =  { 
                'ok' : 0, 
                'message' : { 
                    'code' : 'ESEC000',
                    'text': "Locked User or Not Finished Register"
                } 
            }
            return error, 401            

        payload['session_expired'] = 'false'

        cacheRepository.save(refresh_token_jti, payload, expired_time = int(FINAL_REFRESH_EXPIRES))
        cacheRepository.save(access_jti, payload, expired_time = int(FINAL_ACCESS_EXPIRES))

        userTokens = cacheRepository.getByKey(username)
        userTokens['access_token'] = access_jti
        userTokens['refresh_token'] = refresh_token_jti
        cacheRepository.save(username,userTokens, expired_time = int(FINAL_REFRESH_EXPIRES))

        # Buscar los permisos del usuario y guardarlos en redis
        permissions = MemberGetPermissionsUseCase().execute(username)
        cacheRepository.save(f"{username}{SUFFIX_PERMISSION}", permissions, expired_time = int(FINAL_ACCESS_EXPIRES))

        data = { 'ok': 1,
                'data': { 
                    'extra_info' : {
                        'permissions' : permissions
                    },
                    'access_token': access_token, 
                    'refresh_token': refresh_token_jti 
                    }
                }
        return data, 200


class ProxySecureResource(Resource):
    
    def syncronizePasswordCache(self,password):
        access_token_jti = get_raw_jwt()['jti']
        cacheRepository = CacheRepository()
        cache_payload = cacheRepository.getByKey(access_token_jti)

        cache_payload['password'] = password

        user = GetUserByNameUseCase().execute(cache_payload)
        username = cache_payload['username']

        if user.status == STATUS_ACTIVE:
            cache_payload['person_id'] = username            
            cache_payload['person_extension_id'] = user.person_extension_id
    
        cacheRepository.save(access_token_jti,cache_payload, expired_time = int(ACCESS_EXPIRES))

        userTokens = cacheRepository.getByKey(username)
        refresh_token_jti = userTokens['refresh_token'] 
        
        cacheRepository.save(refresh_token_jti,cache_payload, expired_time = int(REFRESH_EXPIRES))
        
    
    def checkCredentials(self):
        access_token_jti = get_raw_jwt()['jti']
        security_credentials = CacheRepository().getByKey(access_token_jti)
        # This is used for check if the Signup is Finished
        # if security_credentials == None or (not 'person_id' in security_credentials) or ('person_id' in security_credentials and security_credentials['person_id'] is None):
        #     raise ProxyCredentialsNotFound()
        if security_credentials == None or (not 'person_extension_id' in security_credentials) or ('person_extension_id' in security_credentials and security_credentials['person_extension_id'] is None):
            raise ProxyCredentialsNotFound()
        return security_credentials

    def checkForFinishSignup(self):
        access_token_jti = get_raw_jwt()['jti']
        security_credentials = CacheRepository().getByKey(access_token_jti)
        # This is used for check if the Signup is Finished
        # if not ('person_id' in security_credentials and security_credentials['person_id'] is None):
        #     raise ProxyCredentialsNotFound()
        if ('person_extension_id' in security_credentials) and  (security_credentials['person_extension_id'] is None):
            raise ProxyCredentialsNotFound()
        return security_credentials    


# @member_ns.route('/signup')
@v1_api.expect(publicHeader)
class MemberInitSignupResource(Resource):
     
    @member_ns.doc('Member Register')
    @member_ns.expect(mMemberInitRegister)
    def post(self):
        payload = request.json
        n8nClient = N8NClient()
        response = n8nClient.executePost('/webhook/account',payload,False)
        
        if response['ok'] == 1:
            data = MemberInitSignUpUseCase().execute(payload)
            
        return  { 'ok': 1 } , 200
         
# @member_ns.route('/signup/finish')
@v1_api.expect(publicHeader)
class MemberFinishSignupResource(Resource):
     
    @member_ns.doc('Confirm Account')
    @member_ns.expect(mMemberFinishRegister)
    def put(self):
        payload = request.json
        data = MemberFinishRegisterUseCase().execute(payload)
        return  { 'ok': 1 } , 200

@member_ns.route('/profile')
@v1_api.expect(secureHeader)
class MemberProfileResource(ProxySecureResource): 
 
    @member_ns.doc('Member Profile')
    @jwt_required   
    @v1_api.marshal_with(GetProfileUserStruct) 
    def get(self):
        security_credentials = self.checkCredentials()
        query_params = {}
        data = GetDetailedMemberProfileUseCase().execute(security_credentials,query_params)
        # return make_template_response(data, 'json/member/get.json'), 200
        return {'ok' : 1, 'data': data },200

    @member_ns.doc('Update Member Profile')
    @v1_api.expect(UpdateProfileUserStruct)
    @jwt_required    
    def put(self):
        payload = request.json        
        security_credentials = self.checkCredentials()
        payload['id'] = security_credentials['id']
        UpdateMemberProfileUseCase().execute(security_credentials,payload)
        return  { 'ok': 1 }, 200

@member_ns.route('/profile/<email>')
@member_ns.param('email', 'Email Member')
@v1_api.expect(secureHeader)
class GetAnyMemberProfileResource(ProxySecureResource): 

    @member_ns.doc('Get Any Member Profile')
    @jwt_required    
    @v1_api.marshal_with(GetProfileUserStruct) 
    def get(self,email):
        security_credentials = self.checkCredentials()
        query_params = {'email': email}
        data = GetAnyMemberProfileUseCase().execute(security_credentials,query_params)
        return  {'ok' : 1, 'data': data }, 200


@member_ns.route('/password')
@v1_api.expect(secureHeader)
class ChangePasswordMemberResource(ProxySecureResource):
 
    @member_ns.doc('Change Password')
    @v1_api.expect(mChangePassword)    
    @jwt_required    
    def put(self):
        user_payload = request.json
        security_credentials = self.checkCredentials()

        request_payload = { 'id': security_credentials['id'] ,
                   'password': user_payload['new_password'],
                   'old_password': user_payload['old_password']}
        ChangePasswordMemberUseCase().execute(security_credentials,request_payload)
        self.syncronizePasswordCache(user_payload['new_password'])
        return  { 'ok': 1 }, 200


@member_ns.route('/password/reset')
@v1_api.expect(publicHeader)
class InitResetPasswordMemberResource(Resource):

    @member_ns.doc('Reset Password')
    @v1_api.expect(mMemberEmail)    
    def post(self):
        payload = request.json 
        data = InitResetPasswordMemberUseCase().execute(payload)
        return { 'ok': 1 }, 200

@member_ns.route('/password/reset/finish')
@v1_api.expect(publicHeader)
class FinishResetPasswordMemberResource(Resource):

    @member_ns.doc('Finish Reset Password')
    @v1_api.expect(mMemberFinishResetPassword)    
    def put(self):
        payload = request.json 
        data = FinishResetPasswordMemberUseCase().execute(payload)
        return { 'ok': 1 }, 200

@member_ns.route('/unsubscribe')
@v1_api.expect(publicHeader)
class MemberUnsubscribeResource(Resource):
     
    @member_ns.doc('Unsubscribe Account')
    @member_ns.expect(mMemberUnsubscribeRegister)
    def put(self):
        payload = request.json
        data = MemberUnsubscribeRegisterUseCase().execute(payload)
        return  { 'ok': 1 } , 200

@member_ns.route('/signup/resend_confirmation')
@v1_api.expect(publicHeader)
class MemberResendConfirmationRegisterResource(Resource):
     
    @member_ns.doc('Resend Confirmation Email')
    @member_ns.expect(mMemberEmail)
    def post(self):
        payload = request.json
        data = MemberResendConfirmationRegisterUseCase().execute(payload)
        return  { 'ok': 1 } , 200