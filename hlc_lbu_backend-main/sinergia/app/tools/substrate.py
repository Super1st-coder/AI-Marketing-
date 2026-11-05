
from substrateinterface import SubstrateInterface, Keypair
from substrateinterface.exceptions import SubstrateRequestException
from config import config

def singleton(class_):
    instances = {}
    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]
    return getinstance

@singleton
class Substrate(object):
    connection = None

    def create_keypair(self,username):
        keypair = Keypair.create_from_uri(f"//{username}")
        print(keypair.ss58_address)
        return keypair

    def execute_query(self,pallet_name,method_name,params):
        results = self.connection.query( 
            module = pallet_name,
            storage_function = method_name,
            params = params
        )        
        # print(results)        
        return results

    def execute_call(self,keypair,pallet_name,method_name,params):
        call = self.connection.compose_call(
            call_module = pallet_name,
            call_function = method_name,
            call_params = params
        )
        extrinsic = self.connection.create_signed_extrinsic(call=call, keypair=keypair,)
        receipt = None
        try:
            receipt = self.connection.submit_extrinsic(extrinsic,wait_for_inclusion=True)
            print("Extrinsic '{}' sent and included in block '{}'".format(receipt.extrinsic_hash, receipt.block_hash))
        except SubstrateRequestException as e:
            # Arrojar Exception Personalizada
            print("Failed to send: {}".format(e))       
            receipt = None 
        return receipt

    def __init__(self):
        URL = config['dev'].SUBSTRATE_URL
        # print(URL)
        self.connection = SubstrateInterface(
            url=URL,
            ss58_format=42,
            type_registry_preset='substrate-node-template'    
            # type_registry_preset='rococo'    

        )     
        print ("get_version() = %s" % self.connection.version)
        grv=self.connection.rpc_request(method="chain_getRuntimeVersion", params=[])
        print ("chain_getRuntimeVersion()['result']:")
        print(grv['result'])