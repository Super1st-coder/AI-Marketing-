from .base import StrapiRepository
from ..models.entity import content_todict 

class AccountRepository(StrapiRepository):
    def get_by_email(self,email):        
        result = self.get_objects_by_field('accounts','email',email)
        return result[0] if not result is None and len(result) > 0 else None        

    def new(self,email,name):
        return {'email' : email, 'name' : name }

    def create(self,account):
        return self.create_object('accounts',{ 'data' : account })



class ProjectRepository(StrapiRepository):    
    def get_by_account(self,account):        
        results = []
        if account != None:
            account_id = account['id']
            raw_results = self.get_objects_by_field('projects','account_ref',account_id)
            if not raw_results is None and len(raw_results) > 0:
                results = [ content_todict(r) for r in raw_results ]
        return results 

    def get_by_id(self, id):
        results = []
        if id != None:
            raw_results = self.get_objects_by_field('projects', 'id', id)
            if not raw_results is None:
                results = [ content_todict(r) for r in raw_results ]
        return results

    def new(self,account):
        project = None
        if account != None:
            account_id = account['id']
            generated_project = self.generate_new_object("project")
            if not generated_project  is None:
                generated_project['account_ref'] = account_id
                project = generated_project
            else:
                print('Error creating Object... ')
        else:
            # TODO: Raise Exception
            print('Object is REQUIRED ... ')
        return project

    def create(self,project):
        return self.create_object('projects',{ 'data' : project })

    def update(self,project):
        return self.update_object('projects',project['id'],{ 'data' : project })

class SurveyRepository(StrapiRepository):    

    default_project_type = 'B2C'
    default_entity_type = 'bpersona'

    def get_by_project(self,project):        
        results = []
        if project != None:
            project_id = project['id']
            project_type = project['project_type']
            working_collection = f'{project_type.lower()}-{self.default_entity_type.lower()}-surveys'
            raw_results = self.get_objects_by_field(working_collection,'parent_ref',project_id)
            if not raw_results is None:
                results = [ content_todict(r) for r in raw_results ]
        return results 
    
    def new(self,project):
        survey = None
        if not project is None:
            project_id = project['id']
            project_type = project['project_type']            

            working_type = f'{project_type.lower()}-{self.default_entity_type.lower()}-survey'
            generated_survey = self.generate_new_object(working_type)
            if not generated_survey  is None:
                generated_survey['parent_ref'] = project_id
                survey = generated_survey
            else:
                print('Error creating Object... ')
        else:
            # TODO: Raise Exception
            print('Object is REQUIRED ... ')
        return survey

###########################################################################

class BPersonaSurveyRepository(SurveyRepository):
    default_entity_type = 'bpersona'

    def create(self,survey):
        collection = f'{self.default_project_type.lower()}-{self.default_entity_type.lower()}-surveys'
        return self.create_object(collection,{ 'data' : survey })

    def update(self,survey):
        collection = f'{self.default_project_type.lower()}-{self.default_entity_type.lower()}-surveys'
        return self.update_object(collection,survey['id'],{ 'data' : survey })

class ConsultorSurveyRepository(SurveyRepository):    
    default_entity_type = 'consultor'

    def create(self,survey):
        collection = f'{self.default_project_type.lower()}-{self.default_entity_type.lower()}-surveys'
        return self.create_object(collection,{ 'data' : survey })

    def update(self,survey):
        collection = f'{self.default_project_type.lower()}-{self.default_entity_type.lower()}-surveys'
        return self.update_object(collection,survey['id'],{ 'data' : survey })

class ProductoSurveyRepository(SurveyRepository):    
    default_entity_type = 'producto'

    def create(self,survey):
        collection = f'{self.default_project_type.lower()}-{self.default_entity_type.lower()}-surveys'
        return self.create_object(collection,{ 'data' : survey })

    def update(self,survey):
        collection = f'{self.default_project_type.lower()}-{self.default_entity_type.lower()}-surveys'
        return self.update_object(collection,survey['id'],{ 'data' : survey })

###########################################################################

class B2CBPersonaSurveyRepository(BPersonaSurveyRepository):
    default_project_type = 'B2C'


class B2CConsultorSurveyRepository(ConsultorSurveyRepository):    
    default_project_type = 'B2C'


class B2CProductoSurveyRepository(ProductoSurveyRepository):    
    default_project_type = 'B2C'


###########################################################################

class B2BBPersonaSurveyRepository(BPersonaSurveyRepository):
    default_project_type = 'B2B'
    

class B2BConsultorSurveyRepository(ConsultorSurveyRepository):    
    default_project_type = 'B2B'
    

class B2BProductoSurveyRepository(ProductoSurveyRepository):    
    default_project_type = 'B2B'


###########################################################################

class BrandRepository(StrapiRepository):    

    def get_by_project(self,project):        
        results = []
        if project != None:
            project_id = project['id']
            working_collection = 'brands'
            raw_results = self.get_objects_by_field(working_collection,'parent_ref',project_id)
            if not raw_results is None:
                results = [ content_todict(r) for r in raw_results ]
        return results 

    def new(self,project):
        working_object = None
        if not project is None:
            project_id = project['id']

            working_type = 'brand'
            generated_object = self.generate_new_object(working_type)
            if not generated_object  is None:
                generated_object['parent_ref'] = project_id
                working_object = generated_object
            else:
                print('Error creating Object... ')
        else:
            # TODO: Raise Exception
            print('Object is REQUIRED ... ')
        return working_object

    def create(self,working_object):
        collection = 'brands'
        return self.create_object(collection,{ 'data' : working_object })

    def update(self,working_object):
        collection = 'brands'
        return self.update_object(collection,working_object['id'],{ 'data' : working_object })


class BPersonRepository(StrapiRepository):    

    def get_by_project(self,project):        
        results = []
        if project != None:
            project_id = project['id']
            working_collection = 'bpeople'
            raw_results = self.get_objects_by_field(working_collection,'parent_ref',project_id)
            if not raw_results is None:
                results = [ content_todict(r) for r in raw_results ]
        return results 
    
    def get_by_id(self, id):
        results = []
        if id != None:
            raw_results = self.get_objects_by_field('bpeople', 'id', id)
            if not raw_results is None:
                results = [ content_todict(r) for r in raw_results ]
        return results

    def new(self,project):
        working_object = None
        if not project is None:
            project_id = project['id']

            working_type = 'bperson'
            generated_object = self.generate_new_object(working_type)
            if not generated_object  is None:
                generated_object['parent_ref'] = project_id
                working_object = generated_object
            else:
                print('Error creating Object... ')
        else:
            # TODO: Raise Exception
            print('Object is REQUIRED ... ')
        return working_object

    def create(self,working_object):
        collection = 'bpeople'
        return self.create_object(collection,{ 'data' : working_object })

    def update(self,working_object):
        collection = 'bpeople'
        return self.update_object(collection,working_object['id'],{ 'data' : working_object })


class ConsultorSuggestionRepository(StrapiRepository):    

    def get_by_project(self,project):        
        results = []
        if project != None:
            project_id = project['id']
            working_collection = 'consultor-suggestions'
            raw_results = self.get_objects_by_field(working_collection,'parent_ref',project_id)
            if not raw_results is None:
                results = [ content_todict(r) for r in raw_results ]
        return results 
    
    def get_by_id(self, id):
        results = []
        if id != None:
            raw_results = self.get_objects_by_field('consultor-suggestions', 'id', id)
            if not raw_results is None:
                results = [ content_todict(r) for r in raw_results ]
        return results

    def new(self,project):
        working_object = None
        if not project is None:
            project_id = project['id']

            working_type = 'consultor-suggestion'
            generated_object = self.generate_new_object(working_type)
            if not generated_object  is None:
                generated_object['parent_ref'] = project_id
                working_object = generated_object
            else:
                print('Error creating Object... ')
        else:
            # TODO: Raise Exception
            print('Object is REQUIRED ... ')
        return working_object

    def create(self,working_object):
        collection = 'consultor-suggestions'
        return self.create_object(collection,{ 'data' : working_object })

    def update(self,working_object):
        collection = 'consultor-suggestions'
        return self.update_object(collection,working_object['id'],{ 'data' : working_object })


class SalesProcessRepository(StrapiRepository):    

    def get_by_bperson(self,bperson):        
        results = []
        if bperson != None:
            bperson_id = bperson['id']
            working_collection = 'sales-processes'
            raw_results = self.get_objects_by_field(working_collection,'parent_ref',bperson_id)
            if not raw_results is None:
                results = [ content_todict(r) for r in raw_results ]
        return results 

    def new(self,parent):
        working_object = None
        if not parent is None:
            parent_id = parent['id']

            working_type = 'sales-process'
            generated_object = self.generate_new_object(working_type)
            if not generated_object  is None:
                generated_object['parent_ref'] = parent_id
                working_object = generated_object
            else:
                print('Error creating Object... ')
        else:
            # TODO: Raise Exception
            print('Object is REQUIRED ... ')
        return working_object

    def create(self,working_object):
        collection = 'sales-processes'
        return self.create_object(collection,{ 'data' : working_object })

    def update(self,working_object):
        collection = 'sales-processes'
        return self.update_object(collection,working_object['id'],{ 'data' : working_object })


###########################################################################

class ProductRepository(StrapiRepository):    

    def get_by_bperson(self,bperson):        
        results = []
        if bperson != None:
            bperson_id = bperson['id']
            working_collection = 'products'
            raw_results = self.get_objects_by_field(working_collection,'parent_ref',bperson_id)
            if not raw_results is None:
                results = [ content_todict(r) for r in raw_results ]
        return results 

    def new(self,parent):
        working_object = None
        if not parent is None:
            parent_id = parent['id']

            working_type = 'product'
            generated_object = self.generate_new_object(working_type)
            if not generated_object  is None:
                generated_object['parent_ref'] = parent_id
                working_object = generated_object
            else:
                print('Error creating Object... ')
        else:
            # TODO: Raise Exception
            print('Object is REQUIRED ... ')
        return working_object

    def create(self,working_object):
        collection = 'products'
        return self.create_object(collection,{ 'data' : working_object })

    def update(self,working_object):
        collection = 'products'
        return self.update_object(collection,working_object['id'],{ 'data' : working_object })


###########################################################################

class ScenarioRepository(StrapiRepository):    

    def get_by_bperson(self,bperson):        
        results = []
        if bperson != None:
            bperson_id = bperson['id']
            working_collection = 'scenarios'
            raw_results = self.get_objects_by_field(working_collection,'parent_ref',bperson_id)
            if not raw_results is None:
                results = [ content_todict(r) for r in raw_results ]
        return results 

    def new(self,parent):
        working_object = None
        if not parent is None:
            parent_id = parent['id']

            working_type = 'scenario'
            generated_object = self.generate_new_object(working_type)
            if not generated_object  is None:
                generated_object['parent_ref'] = parent_id
                working_object = generated_object
            else:
                print('Error creating Object... ')
        else:
            # TODO: Raise Exception
            print('Object is REQUIRED ... ')
        return working_object

    def create(self,working_object):
        collection = 'scenarios'
        return self.create_object(collection,{ 'data' : working_object })

    def update(self,working_object):
        collection = 'scenarios'
        return self.update_object(collection,working_object['id'],{ 'data' : working_object })


###########################################################################

class ScenarioContextRepository(StrapiRepository):    

    def get_by_bperson(self,bperson):        
        results = []
        if bperson != None:
            bperson_id = bperson['id']
            working_collection = 'scenario-contexts'
            raw_results = self.get_objects_by_field(working_collection,'parent_ref',bperson_id)
            if not raw_results is None:
                results = [ content_todict(r) for r in raw_results ]
        return results 

    def new(self,parent):
        working_object = None
        if not parent is None:
            parent_id = parent['id']

            working_type = 'scenario-context'
            generated_object = self.generate_new_object(working_type)
            if not generated_object  is None:
                generated_object['parent_ref'] = parent_id
                working_object = generated_object
            else:
                print('Error creating Object... ')
        else:
            # TODO: Raise Exception
            print('Object is REQUIRED ... ')
        return working_object

    def create(self,working_object):
        collection = 'scenario-contexts'
        return self.create_object(collection,{ 'data' : working_object })

    def update(self,working_object):
        collection = 'scenario-contexts'
        return self.update_object(collection,working_object['id'],{ 'data' : working_object })


###########################################################################

class ScenarioActivityRepository(StrapiRepository):    

    def get_by_scenario(self,scenario):        
        results = []
        if scenario != None:
            bperson_id = scenario['id']
            working_collection = 'scenario-activities'
            raw_results = self.get_objects_by_field(working_collection,'parent_ref',bperson_id)
            if not raw_results is None:
                results = [ content_todict(r) for r in raw_results ]
        return results 

    def new(self,parent):
        working_object = None
        if not parent is None:
            parent_id = parent['id']

            working_type = 'scenario-activity'
            generated_object = self.generate_new_object(working_type)
            if not generated_object  is None:
                generated_object['parent_ref'] = parent_id
                working_object = generated_object
            else:
                print('Error creating Object... ')
        else:
            # TODO: Raise Exception
            print('Object is REQUIRED ... ')
        return working_object

    def create(self,working_object):
        collection = 'scenario-activities'
        return self.create_object(collection,{ 'data' : working_object })

    def update(self,working_object):
        collection = 'scenario-activities'
        return self.update_object(collection,working_object['id'],{ 'data' : working_object })


###########################################################################

class PromptRepository(StrapiRepository):    

    def get_by_project(self,project):        
        results = []
        if project != None:
            project_id = project['id']
            working_collection = 'prompts'
            raw_results = self.get_objects_by_field(working_collection,'parent_ref',project_id)
            if not raw_results is None:
                results = [ content_todict(r) for r in raw_results ]
        return results 

    def new(self,project):
        working_object = None
        if not project is None:
            project_id = project['id']

            working_type = 'prompt'
            generated_object = self.generate_new_object(working_type)
            if not generated_object  is None:
                generated_object['parent_ref'] = project_id
                working_object = generated_object
            else:
                print('Error creating Object... ')
        else:
            # TODO: Raise Exception
            print('Object is REQUIRED ... ')
        return working_object

    def create(self,working_object):
        collection = 'prompts'
        return self.create_object(collection,{ 'data' : working_object })

    def update(self,working_object):
        collection = 'prompts'
        return self.update_object(collection,working_object['id'],{ 'data' : working_object })

class AgentRepository(StrapiRepository):    

    def get_by_project(self,project):        
        results = []
        if project != None:
            project_id = project['id']
            working_collection = 'agents'
            raw_results = self.get_objects_by_field(working_collection,'parent_ref',project_id)
            if not raw_results is None:
                results = [ content_todict(r) for r in raw_results ]
        return results 

    def new(self,project):
        working_object = None
        if not project is None:
            project_id = project['id']

            working_type = 'agent'
            generated_object = self.generate_new_object(working_type)
            if not generated_object  is None:
                generated_object['parent_ref'] = project_id
                working_object = generated_object
            else:
                print('Error creating Object... ')
        else:
            # TODO: Raise Exception
            print('Object is REQUIRED ... ')
        return working_object

    def create(self,working_object):
        collection = 'agents'
        return self.create_object(collection,{ 'data' : working_object })

    def update(self,working_object):
        collection = 'agents'
        return self.update_object(collection,working_object['id'],{ 'data' : working_object })

