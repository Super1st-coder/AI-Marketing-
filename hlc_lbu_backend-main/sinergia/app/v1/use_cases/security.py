'''
Created on 17 dic. 2019

@author: ramon
'''
from app.v1.repository.security import SecurityElementRepository, UserRepository
from app.v1.repository.security import MemberRepository

class AuthenticateUseCase(object):
    securityElementRepository = SecurityElementRepository()
    
    def execute(self,username_or_token,password):
        security_element = self.securityElementRepository.getByAuthToken(username_or_token)
        if not security_element:
            security_element = self.securityElementRepository.getByName(username_or_token)
            if not security_element or not security_element.verify_password(password):
                return None
            else:
                return security_element
        else:
            return security_element

class GetUserByNameUseCase(object):
    def execute(self,payload):
        return UserRepository().getByName(payload['username'])


class GetMemberProfileUseCase(object):
    def execute(self,security_credentials,payload):
        return MemberRepository(username=security_credentials['username']).get(payload)


class GetDetailedMemberProfileUseCase(object):
    def execute(self,security_credentials,payload):
        return MemberRepository(username=security_credentials['username']).get(payload,full=True)

class GetAnyMemberProfileUseCase(object):
    def execute(self,security_credentials,payload):
        return MemberRepository(username=security_credentials['username']).getByEmail(payload['email'])

class UpdateMemberProfileUseCase(object):
    def execute(self,security_credentials,payload):
        MemberRepository(username=security_credentials['username']).save(payload)

class ChangePasswordMemberUseCase(object):
    def execute(self,security_credentials,payload):
        MemberRepository(username=security_credentials['username']).changePassword(payload)

class InitResetPasswordMemberUseCase(object):
    def execute(self,payload):
        return MemberRepository().initResetPassword(payload)

class FinishResetPasswordMemberUseCase(object):
    def execute(self,payload):
        return MemberRepository().finishResetPassword(payload)

class MemberInitSignUpUseCase(object):
    def execute(self,payload):
        return MemberRepository().initCreate(payload)

class MemberFinishRegisterUseCase(object):
    def execute(self,payload):
        return MemberRepository().finishCreate(payload)

class MemberUnsubscribeRegisterUseCase(object):
    def execute(self,payload):
        return MemberRepository().unsubscribe(payload)
    
class MemberResendConfirmationRegisterUseCase(object):
    def execute(self,payload):
        return MemberRepository().resendConfirmation(payload)
    
class MemberGetPermissionsUseCase(object):
    def execute(self,payload):
        return MemberRepository().gerPermissionsByUsername(payload)