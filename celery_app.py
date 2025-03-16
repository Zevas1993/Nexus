"""
Celery configuration for Nexus AI Assistant.

This module provides Celery configuration and task registration.
"""

from typing import Dict, Any
import logging
from celery import Celery
from ...infrastructure.context import ApplicationContext

logger = logging.getLogger(__name__)

def create_celery_app(app_context: ApplicationContext) -> Celery:
    """Create Celery application.
    
    Args:
        app_context: Application context
        
    Returns:
        Celery application
    """
    config = app_context.config
    broker_url = config.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    result_backend = config.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
    
    celery_app = Celery(
        'nexus',
        broker=broker_url,
        backend=result_backend
    )
    
    # Configure Celery
    celery_app.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        task_track_started=True,
        task_time_limit=3600,  # 1 hour
        worker_max_tasks_per_child=200,
        worker_prefetch_multiplier=1
    )
    
    # Add any additional configuration from app_context
    celery_config = {k: v for k, v in config.items() if k.startswith('CELERY_')}
    celery_app.conf.update(celery_config)
    
    logger.info("Celery application created")
    return celery_app

# Create a placeholder Celery app for task registration
# This will be replaced with the real app when initialized
celery_app = Celery('nexus')

@celery_app.task(name='nexus.tasks.long_running_task')
def long_running_task(data: Dict[str, Any]) -> Dict[str, Any]:
    """Example long-running task.
    
    Args:
        data: Task data
        
    Returns:
        Task result
    """
    import time
    
    logger.info(f"Starting long-running task with data: {data}")
    
    # Simulate long-running task
    time.sleep(10)
    
    result = {
        "status": "completed",
        "input_data": data,
        "result": "Task completed successfully"
    }
    
    logger.info(f"Completed long-running task: {result}")
    return result

@celery_app.task(name='nexus.tasks.index_documents')
def index_documents(documents: list, collection: str = 'default') -> Dict[str, Any]:
    """Index documents for RAG.
    
    Args:
        documents: List of documents to index
        collection: Collection name
        
    Returns:
        Indexing result
    """
    from ...domain.rag.indexing import IndexingService, Document
    
    logger.info(f"Indexing {len(documents)} documents in collection {collection}")
    
    # This is a placeholder. In a real implementation, you would
    # get the IndexingService from the application context.
    indexing_service = IndexingService()
    
    results = []
    for doc_data in documents:
        # Convert to Document object
        if isinstance(doc_data, dict):
            doc = Document(
                content=doc_data.get('content', ''),
                metadata=doc_data.get('metadata', {}),
                doc_id=doc_data.get('id')
            )
        else:
            doc = Document(content=str(doc_data))
        
        # Index document
        result = indexing_service._process_impl(
            '',
            document=doc,
            collection=collection
        )
        results.append(result)
    
    return {
        "status": "completed",
        "collection": collection,
        "document_count": len(documents),
        "results": results
    }

@celery_app.task(name='nexus.tasks.system_maintenance')
def system_maintenance() -> Dict[str, Any]:
    """Perform system maintenance tasks.
    
    Returns:
        Maintenance result
    """
    import time
    from ...application.services.system_service import SystemService
    
    logger.info("Starting system maintenance")
    start_time = time.time()
    
    # This is a placeholder. In a real implementation, you would
    # get the SystemService from the application context.
    system_service = SystemService(None)
    
    # Check system health
    health = system_service.check_health()
    
    # Perform maintenance tasks based on health
    maintenance_tasks = []
    
    if health["status"] == "warning":
        # Example maintenance tasks
        if health["checks"]["disk"]["status"] == "warning":
            # Clean up temporary files
            maintenance_tasks.append("disk_cleanup")
        
        if health["checks"]["memory"]["status"] == "warning":
            # Restart memory-intensive services
            maintenance_tasks.append("memory_optimization")
    
    duration = time.time() - start_time
    
    return {
        "status": "completed",
        "health_status": health["status"],
        "maintenance_tasks": maintenance_tasks,
        "duration": duration
    }
