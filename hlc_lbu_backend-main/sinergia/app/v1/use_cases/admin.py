'''
Created on 17 dic. 2019

@author: ramon
'''
from app.v1.repository.security import SecurityElementRepository, UserRepository
from app.v1.repository.admin import MemberRepository, RolRepository

class GetAdminMemberListUseCase(object):
    def execute(self,security_credentials,query_params):
        return MemberRepository(username=security_credentials['username']).get(query_params)

class GetAdminMemberUseCase(object):
    def execute(self,security_credentials,query_params):
        return MemberRepository(username=security_credentials['username']).getByUsername(query_params['username'])
    
class DeleteAdminMemberUseCase(object):
    def execute(self,security_credentials,query_params):
        return MemberRepository(username=security_credentials['username']).deleteByUsername(query_params['username'])
    
class GetAdminMemberByTypeUseCase(object):
    def execute(self,security_credentials,query_params):
        return MemberRepository(username=security_credentials['username']).getByUsernameAndType(query_params['username'], query_params['user_type'])

class DeleteAdminMemberByTypeUseCase(object):
    def execute(self,security_credentials,query_params):
        return MemberRepository(username=security_credentials['username']).deleteByUsernameAndType(query_params['username'], query_params['user_type'])

class ReactivateAdminMemberByTypeUseCase(object):
    def execute(self,security_credentials,query_params):
        return MemberRepository(username=security_credentials['username']).reactivateByUsernameAndType(query_params['username'], query_params['user_type'])

class CreateAdminMemberUseCase(object):
    def execute(self,security_credentials,payload, user_type):
        return MemberRepository(username=security_credentials['username']).new(payload, user_type)

class SaveAdminMemberUseCase(object):
    def execute(self,security_credentials,payload):
        MemberRepository(username=security_credentials['username']).save(payload)

class GetRolListUseCase(object):
    def execute(self,security_credentials,query_params):
        return RolRepository(username=security_credentials['username']).get(query_params)

class SaveRolUseCase(object):
    def execute(self,security_credentials,payload):
        return RolRepository(username=security_credentials['username']).save(payload)

class UpdateAdminMemberUseCase(object):
    def execute(self,security_credentials,payload):
        return MemberRepository(username=security_credentials['username']).update(payload)
    
class SendInviteAdminMemberUseCase(object):
    def execute(self,security_credentials,payload):
        MemberRepository(username=security_credentials['username']).sendInvite(payload)

class MemberFinishRegisterUseCase(object):
    def execute(self,payload):
        return MemberRepository().finishCreate(payload)
    
class GetRoleUseCase(object):
    def execute(self,security_credentials,query_params):
        return RolRepository(username=security_credentials['username']).getById(query_params['role_id'])
    
class DropAdminMemberUseCase(object):
    def execute(self,security_credentials,query_params):
        return MemberRepository(username=security_credentials['username']).dropByUsername(query_params['username'])