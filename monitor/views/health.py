"""
Health check view for monitoring service availability.
"""
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


def health_check(request):
    """
    Health check endpoint for load balancers and monitoring services.
    
    Returns JSON with status of:
    - Database connection
    - Redis cache connection
    - Overall health status
    
    Returns:
        200 if healthy
        503 if any component is unhealthy
    """
    checks = {
        'status': 'unhealthy',
        'timestamp': timezone.now().isoformat(),
        'checks': {
            'database': False,
            'cache': False,
        }
    }
    
    # Check database connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result == (1,):
                checks['checks']['database'] = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        checks['checks']['database'] = False
    
    # Check Redis cache connection
    try:
        test_key = 'health_check_test'
        test_value = 'ok'
        cache.set(test_key, test_value, timeout=10)
        
        if cache.get(test_key) == test_value:
            checks['checks']['cache'] = True
            cache.delete(test_key)
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        checks['checks']['cache'] = False
    
    # Overall health status
    if all(checks['checks'].values()):
        checks['status'] = 'healthy'
        return JsonResponse(checks, status=200)
    else:
        return JsonResponse(checks, status=503)


def readiness_check(request):
    """
    Readiness check for Kubernetes/container orchestration.
    
    Returns 200 if application is ready to receive traffic.
    """
    # Could add more complex checks here
    # For now, just check if we can respond
    return JsonResponse({'status': 'ready'}, status=200)


def liveness_check(request):
    """
    Liveness check for Kubernetes/container orchestration.
    
    Returns 200 if application process is running.
    """
    return JsonResponse({'status': 'alive'}, status=200)
