import logging
from app.v2 import v2_api
from app.v1.resources.base import ProxySecureResource, secureHeader
from flask_jwt_extended.view_decorators import jwt_required
from celery.result import AsyncResult

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

tasks_ns = v2_api.namespace('tasks', description='Async and Scheduled Tasks')


@tasks_ns.route('/result/<task_id>')
@v2_api.expect(secureHeader)
class AsyncTaskResource(ProxySecureResource):

    @tasks_ns.doc('Get Task Result')
    @jwt_required
    def get(self, task_id):
        result = AsyncResult(task_id)
        ready = result.ready()
        successful = result.successful()
        
        value = None
        if ready:
            if successful:
                value = result.result
            else:
                value = {
                    'error': str(result.result),
                    'type': type(result.result).__name__,
                    'traceback': getattr(result, 'traceback', None)
                }
                
        return {
            'ok': 1,
            'data': {
                'ready': ready,
                'successful': successful,
                'value': value,
            }
        }
        