from flask_babel import gettext

class SinergiaException(Exception):
    def __init__(self, code='ESIN001', text=None, *args, **kwargs):
        self.code = code
        if text is None:
            i18_text = gettext(self.code)
            self.text = i18_text if i18_text != self.code else 'Unknown Error'
        else:
            self.text = text
        super().__init__(self.text, *args, **kwargs)

    def __str__(self):
        return str(self.text)

class ConnectionException(SinergiaException):
    def __init__(self,text=None):
        super(ConnectionException, self).__init__(code='EHTTP001',text = text)
        
class CryptoPOSException(SinergiaException):
    def __init__(self, text=None):
        super(CryptoPOSException, self).__init__(code='EPOS001',text = text)

class BiostartException(SinergiaException):
    def __init__(self, text=None):
        super(BiostartException, self).__init__(code='BIOS001',text = text)

class N8NException(SinergiaException):
    def __init__(self, text=None):
        super(N8NException, self).__init__(code='N8N001',text = text)

class StrapiException(SinergiaException):
    def __init__(self, text=None):
        super(StrapiException, self).__init__(code='STRAPI001',text = text)

class ImageLibraryException(SinergiaException):
    def __init__(self, text=None):
        super(ImageLibraryException, self).__init__(code='IMG001', text = text)

class ProxyCredentialsNotFound(SinergiaException):
    def __init__(self,text=None):
        super(ProxyCredentialsNotFound, self).__init__(code='ESIN002',text = text)    

class NotImplementedException(SinergiaException):
    def __init__(self,text=None):
        super(NotImplementedException, self).__init__(code='NOTIMP001',text = text)

class UserCurrentPasswordException(SinergiaException):
    def __init__(self,text=None):
        super(UserCurrentPasswordException, self).__init__(code='USRPWD001',text = text)

class UserRepeatedPasswordException(SinergiaException):
    def __init__(self,text=None):
        super(UserRepeatedPasswordException, self).__init__(code='USRPWD002',text = text)

class IncorrectValidationException(SinergiaException):
    def __init__(self, text=None, errors=None):
        if errors is None and isinstance(text, (dict, list)):
            errors = text
            text = "Validation Failed"
        
        super(IncorrectValidationException, self).__init__(code='SYSVAL001', text=text)
        self.errors = errors

class IntegrityException(SinergiaException):
    def __init__(self,text=None):
        super(IntegrityException, self).__init__(code='INT001',text = text)

class DatabaseException(SinergiaException):
    def __init__(self,text=None):
        super(DatabaseException, self).__init__(code='DB001',text = text)

class DataNotFoundException(SinergiaException):
    def __init__(self,text=None):
        super(DataNotFoundException, self).__init__(code='DAT001',text = text)

class DataAlreadyRegisteredException(SinergiaException):
    def __init__(self,text=None):
        super(DataAlreadyRegisteredException, self).__init__(code='DAT003',text = text)

class DeleteDataException(SinergiaException):
    def __init__(self,text=None):
        super(DeleteDataException, self).__init__(code='DAT002',text = text)

class ParametersNotFoundException(SinergiaException):
    def __init__(self,text=None):
        super(ParametersNotFoundException, self).__init__(code='PAR001',text = text)

class RepositoryUnknownException(SinergiaException):
    def __init__(self,text=None):
        super(RepositoryUnknownException, self).__init__(code='REP001',text = text)

class RESTClientException(SinergiaException):
    def __init__(self, text=None):
        super(RESTClientException, self).__init__(code='AIR001',text = text)

class NotAccessException(SinergiaException):
    def __init__(self,text='Access Denied'):
        super(NotAccessException, self).__init__(code='ACC001',text = text)

class S3ClientException(SinergiaException):
    def __init__(self, text=None):
        super(S3ClientException, self).__init__(code='S3001',text = text)

class PermissionDeniedException(SinergiaException):
    def __init__(self,text='Permissions Error'):
        super(PermissionDeniedException, self).__init__(code='PERM001',text = text)

class RateLimitExceededException(SinergiaException):
    def __init__(self,text='Rate Limit Exceeded'):
        super(RateLimitExceededException, self).__init__(code='RATE001',text = text)

class AbyssaleException(SinergiaException):
    def __init__(self, text=None):
        super(AbyssaleException, self).__init__(code='ABY001', text = text)

class FuryException(SinergiaException):
    def __init__(self, text=None):
        super(FuryException, self).__init__(code='FURY001', text = text)

class MetaException(SinergiaException):
    def __init__(self, code=None, text=None):
        self.code = code or 'META001'
        super(MetaException, self).__init__(code=self.code, text=text)


