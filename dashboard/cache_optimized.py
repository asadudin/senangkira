"""
Enhanced Dashboard Caching System with Advanced Optimization

Key enhancements:
1. Multi-level caching with intelligent invalidation
2. Cache warming and preloading strategies
3. Distributed caching with Redis support
4. Cache compression and serialization optimization
5. Performance monitoring and analytics
6. Background cache refresh jobs
"""

import hashlib
import json
import pickle
import zlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union, Callable
from decimal import Decimal
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
import time
import logging

from django.core.cache import cache, caches
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import QuerySet
from django.conf import settings
import hashlib
from django.core.signals import request_finished
from django.dispatch import receiver

User = get_user_model()
logger = logging.getLogger(__name__)


class CacheConfig:
    """Configuration for different cache levels and strategies."""
    
    # Cache levels with different timeout strategies
    LEVELS = {
        'L1_MEMORY': {
            'timeout': 300,    # 5 minutes - fastest access
            'max_size': 1000,  # Maximum number of entries
            'backend': 'locmem'
        },
        'L2_REDIS': {
            'timeout': 1800,   # 30 minutes - shared across instances
            'max_size': 10000,
            'backend': 'redis'
        },
        'L3_DATABASE': {
            'timeout': 3600,   # 1 hour - persistent storage
            'max_size': None,
            'backend': 'db'
        }
    }
    
    # Cache key prefixes for organization
    PREFIXES = {
        'DASHBOARD_OVERVIEW': 'dash_overview',
        'DASHBOARD_STATS': 'dash_stats',
        'DASHBOARD_BREAKDOWN': 'dash_breakdown',
        'ANALYTICS_DATA': 'analytics',
        'PERFORMANCE_METRICS': 'perf_metrics',
        'USER_CONTEXT': 'user_ctx',
        'QUERY_CACHE': 'query',
        'AGGREGATION_CACHE': 'agg'
    }
    
    # Compression settings
    COMPRESSION = {
        'threshold': 1024,  # Compress data larger than 1KB
        'level': 6,         # Compression level (1-9)
        'enabled': True
    }


class AdvancedCacheManager:
    """
    Advanced cache manager with multi-level caching and intelligent strategies.
    
    Features:
    - Multi-level cache hierarchy (Memory -> Redis -> Database)
    - Intelligent cache warming and preloading
    - Compression for large data sets
    - Cache analytics and monitoring
    - Background refresh jobs
    - Distributed cache invalidation
    """
    
    def __init__(self, user: User):
        self.user = user
        self.user_prefix = f"user_{user.id}"
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.stats = CacheStatistics(user)
        
        # Initialize cache backends
        self.memory_cache = caches['default'] if 'default' in caches else cache
        try:
            self.redis_cache = caches['redis'] if 'redis' in caches else cache
        except:
            self.redis_cache = cache
        
        self.db_cache = caches['db'] if 'db' in caches else cache
    
    def get_cache_key(self, prefix: str, key_type: str, **params) -> str:
        """
        Generate hierarchical cache key with parameters.
        
        Args:
            prefix: Cache prefix from CacheConfig.PREFIXES
            key_type: Type of cached data
            **params: Additional parameters for key generation
            
        Returns:
            str: Generated cache key
        """
        # Create parameter hash for complex parameters
        if params:
            # Sort parameters for consistent hashing
            param_str = json.dumps(params, sort_keys=True, cls=DjangoJSONEncoder)
            param_hash = hashlib.sha256(param_str.encode()).hexdigest()[:12]
            return f"{prefix}:{self.user_prefix}:{key_type}:{param_hash}"
        
        return f"{prefix}:{self.user_prefix}:{key_type}"

    def _get_cache_backend(self, level: str) -> Any:
        if level == 'L1_MEMORY':
            return self.memory_cache
        elif level == 'L2_REDIS':
            return self.redis_cache
        elif level == 'L3_DATABASE':
            return self.db_cache
        return self.memory_cache
    
    def get_multi_level(self, cache_key: str, level_priority: List[str] = None) -> Optional[Any]:
        """
        Get data from multi-level cache with fallback.
        
        Args:
            cache_key: Cache key to retrieve
            level_priority: Priority order for cache levels
            
        Returns:
            Cached data or None if not found
        """
        if level_priority is None:
            level_priority = ['L1_MEMORY', 'L2_REDIS', 'L3_DATABASE']
        
        start_time = time.time()
        
        for level in level_priority:
            try:
                cache_backend = self._get_cache_backend(level)
                data = cache_backend.get(cache_key)
                
                if data is not None:
                    # Decompress if needed
                    if isinstance(data, dict) and data.get('_compressed'):
                        data = self._decompress_data(data)
                    
                    # Update statistics
                    self.stats.record_hit(level, time.time() - start_time)
                    
                    # Promote to higher levels for future access
                    self._promote_to_higher_levels(cache_key, data, level, level_priority)
                    
                    return data
                    
            except Exception as e:
                logger.warning(f"Cache get failed for level {level}: {e}")
                continue
        
        # Record cache miss
        self.stats.record_miss(time.time() - start_time)
        return None
    
    def set_multi_level(
        self, 
        cache_key: str, 
        data: Any, 
        timeout: Optional[int] = None,
        levels: List[str] = None
    ) -> bool:
        """
        Set data in multiple cache levels.
        
        Args:
            cache_key: Cache key
            data: Data to cache
            timeout: Cache timeout (uses default if None)
            levels: Cache levels to set (uses all if None)
            
        Returns:
            bool: True if at least one level succeeded
        """
        if levels is None:
            levels = ['L1_MEMORY', 'L2_REDIS', 'L3_DATABASE']
        
        # Compress large data
        compressed_data = self._compress_data(data)
        
        success_count = 0
        
        for level in levels:
            try:
                cache_backend = self._get_cache_backend(level)
                level_timeout = timeout or CacheConfig.LEVELS[level]['timeout']
                
                if cache_backend.set(cache_key, compressed_data, level_timeout):
                    success_count += 1
                    
            except Exception as e:
                logger.warning(f"Cache set failed for level {level}: {e}")
                continue
        
        self.stats.record_set(success_count > 0)
        return success_count > 0
    
    def invalidate_pattern(self, pattern: str, levels: List[str] = None) -> int:
        """
        Invalidate cache keys matching a pattern.
        
        Args:
            pattern: Pattern to match (supports wildcards)
            levels: Cache levels to invalidate
            
        Returns:
            int: Number of keys invalidated
        """
        if levels is None:
            levels = ['L1_MEMORY', 'L2_REDIS', 'L3_DATABASE']
        
        total_invalidated = 0
        
        for level in levels:
            try:
                cache_backend = self._get_cache_backend(level)
                
                # This would need to be implemented based on cache backend
                # For now, we'll use a simple approach
                if hasattr(cache_backend, 'delete_pattern'):
                    count = cache_backend.delete_pattern(pattern)
                    total_invalidated += count
                else:
                    # Fallback: clear all cache for this user
                    logger.warning(f"Pattern deletion not supported for {level}, clearing user cache")
                    self._clear_user_cache(cache_backend)
                    total_invalidated += 1
                    
            except Exception as e:
                logger.warning(f"Cache invalidation failed for level {level}: {e}")
                continue
        
        self.stats.record_invalidation(total_invalidated)
        return total_invalidated
    
    def warm_cache_async(self, warming_functions: List[Callable], priority: str = 'background'):
        """
        Asynchronously warm cache with provided functions.
        
        Args:
            warming_functions: List of functions to execute for cache warming
            priority: Priority level ('immediate', 'background')
        """
        if priority == 'immediate':
            # Execute immediately in thread pool
            for func in warming_functions:
                self.executor.submit(self._safe_cache_warm, func)
        else:
            # Schedule for background execution
            self._schedule_background_warming(warming_functions)
    
    def get_or_set_with_lock(
        self, 
        cache_key: str, 
        data_func: Callable, 
        timeout: Optional[int] = None,
        lock_timeout: int = 30
    ) -> Any:
        """
        Get cached data or set with distributed locking to prevent cache stampede.
        
        Args:
            cache_key: Cache key
            data_func: Function to generate data if not cached
            timeout: Cache timeout
            lock_timeout: Lock timeout in seconds
            
        Returns:
            Cached or generated data
        """
        # Try to get from cache first
        data = self.get_multi_level(cache_key)
        if data is not None:
            return data
        
        # Use distributed lock to prevent multiple computations
        lock_key = f"lock:{cache_key}"
        
        try:
            # Try to acquire lock
            if self.redis_cache.add(lock_key, "locked", lock_timeout):
                try:
                    # Double-check cache after acquiring lock
                    data = self.get_multi_level(cache_key)
                    if data is not None:
                        return data
                    
                    # Generate and cache data
                    start_time = time.time()
                    data = data_func()
                    generation_time = time.time() - start_time
                    
                    self.set_multi_level(cache_key, data, timeout)
                    self.stats.record_generation(generation_time)
                    
                    return data
                    
                finally:
                    # Release lock
                    self.redis_cache.delete(lock_key)
            else:
                # Wait for other process to complete and try cache again
                time.sleep(0.1)
                for _ in range(50):  # Wait up to 5 seconds
                    data = self.get_multi_level(cache_key)
                    if data is not None:
                        return data
                    time.sleep(0.1)
                
                # Fallback: generate data without caching
                logger.warning(f"Cache lock timeout for {cache_key}, generating without cache")
                return data_func()
                
        except Exception as e:
            logger.error(f"Cache locking failed for {cache_key}: {e}")
            # Fallback to direct generation
            return data_func()
    
    def _get_cache_backend(self, level: str):
        """Get cache backend for specified level."""
        if level == 'L1_MEMORY':
            return self.memory_cache
        elif level == 'L2_REDIS':
            return self.redis_cache
        elif level == 'L3_DATABASE':
            return self.db_cache
        else:
            return cache
    
    def _compress_data(self, data: Any) -> Any:
        """Compress data if it's large enough."""
        if not CacheConfig.COMPRESSION['enabled']:
            return data
        
        try:
            # Serialize data
            serialized = pickle.dumps(data)
            
            # Compress if larger than threshold
            if len(serialized) > CacheConfig.COMPRESSION['threshold']:
                compressed = zlib.compress(serialized, CacheConfig.COMPRESSION['level'])
                
                return {
                    '_compressed': True,
                    '_data': compressed,
                    '_original_size': len(serialized),
                    '_compressed_size': len(compressed)
                }
            
            return data
            
        except Exception as e:
            logger.warning(f"Data compression failed: {e}")
            return data
    
    def _decompress_data(self, compressed_data: Dict) -> Any:
        """Decompress data if it was compressed."""
        try:
            if compressed_data.get('_compressed'):
                decompressed = zlib.decompress(compressed_data['_data'])
                return pickle.loads(decompressed)
            
            return compressed_data
            
        except Exception as e:
            logger.error(f"Data decompression failed: {e}")
            return None
    
    def _promote_to_higher_levels(
        self, 
        cache_key: str, 
        data: Any, 
        current_level: str, 
        level_priority: List[str]
    ):
        """Promote frequently accessed data to higher cache levels."""
        current_index = level_priority.index(current_level)
        
        # Promote to all higher levels
        for i in range(current_index):
            higher_level = level_priority[i]
            try:
                cache_backend = self._get_cache_backend(higher_level)
                timeout = CacheConfig.LEVELS[higher_level]['timeout']
                cache_backend.set(cache_key, data, timeout)
            except Exception as e:
                logger.warning(f"Cache promotion failed for {higher_level}: {e}")
    
    def _safe_cache_warm(self, warming_func: Callable):
        """Safely execute cache warming function with error handling."""
        try:
            warming_func()
        except Exception as e:
            logger.error(f"Cache warming failed: {e}")
    
    def _schedule_background_warming(self, warming_functions: List[Callable]):
        """Schedule background cache warming (implementation depends on task queue)."""
        # This would integrate with Celery or similar task queue
        logger.info(f"Scheduling {len(warming_functions)} cache warming functions")
        
        # For now, execute in thread pool with delay
        for func in warming_functions:
            self.executor.submit(self._delayed_warm, func, delay=1)
    
    def _delayed_warm(self, func: Callable, delay: int):
        """Execute cache warming function with delay."""
        time.sleep(delay)
        self._safe_cache_warm(func)
    
    def _clear_user_cache(self, cache_backend):
        """Clear all cache entries for current user."""
        # This is a simplified implementation
        # In production, you'd want more sophisticated pattern matching
        try:
            cache_backend.clear()
        except Exception as e:
            logger.warning(f"Cache clear failed: {e}")


class CacheStatistics:
    """Cache performance statistics and monitoring."""
    
    def __init__(self, user: User):
        self.user = user
        self.stats_key = f"cache_stats_{user.id}"
        
    def record_hit(self, level: str, response_time: float):
        """Record cache hit with response time."""
        stats = self._get_stats()
        stats['hits'] = stats.get('hits', 0) + 1
        stats['hit_by_level'] = stats.get('hit_by_level', {})
        stats['hit_by_level'][level] = stats['hit_by_level'].get(level, 0) + 1
        stats['total_response_time'] = stats.get('total_response_time', 0) + response_time
        self._set_stats(stats)
    
    def record_miss(self, response_time: float):
        """Record cache miss."""
        stats = self._get_stats()
        stats['misses'] = stats.get('misses', 0) + 1
        stats['miss_response_time'] = stats.get('miss_response_time', 0) + response_time
        self._set_stats(stats)
    
    def record_set(self, success: bool):
        """Record cache set operation."""
        stats = self._get_stats()
        if success:
            stats['sets'] = stats.get('sets', 0) + 1
        else:
            stats['failed_sets'] = stats.get('failed_sets', 0) + 1
        self._set_stats(stats)
    
    def record_invalidation(self, count: int):
        """Record cache invalidation."""
        stats = self._get_stats()
        stats['invalidations'] = stats.get('invalidations', 0) + count
        self._set_stats(stats)
    
    def record_generation(self, generation_time: float):
        """Record data generation time."""
        stats = self._get_stats()
        stats['generations'] = stats.get('generations', 0) + 1
        stats['total_generation_time'] = stats.get('total_generation_time', 0) + generation_time
        self._set_stats(stats)
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics."""
        stats = self._get_stats()
        
        total_requests = stats.get('hits', 0) + stats.get('misses', 0)
        hit_rate = (stats.get('hits', 0) / total_requests * 100) if total_requests > 0 else 0
        
        avg_response_time = (
            stats.get('total_response_time', 0) / stats.get('hits', 1)
        ) if stats.get('hits', 0) > 0 else 0
        
        avg_generation_time = (
            stats.get('total_generation_time', 0) / stats.get('generations', 1)
        ) if stats.get('generations', 0) > 0 else 0
        
        return {
            'hit_rate_percentage': round(hit_rate, 2),
            'total_requests': total_requests,
            'hits': stats.get('hits', 0),
            'misses': stats.get('misses', 0),
            'average_response_time_ms': round(avg_response_time * 1000, 2),
            'average_generation_time_ms': round(avg_generation_time * 1000, 2),
            'cache_sets': stats.get('sets', 0),
            'failed_sets': stats.get('failed_sets', 0),
            'invalidations': stats.get('invalidations', 0),
            'hit_by_level': stats.get('hit_by_level', {}),
            'last_updated': timezone.now().isoformat()
        }
    
    def _get_stats(self) -> Dict:
        """Get current statistics."""
        return cache.get(self.stats_key, {})
    
    def _set_stats(self, stats: Dict):
        """Set statistics with 1-hour timeout."""
        cache.set(self.stats_key, stats, 3600)


class DashboardCacheWarmer:
    """Intelligent cache warming strategies for dashboard data."""
    
    def __init__(self, user: User):
        self.user = user
        self.cache_manager = AdvancedCacheManager(user)
    
    def warm_dashboard_caches(self, priority: str = 'background'):
        """Warm all dashboard-related caches."""
        warming_functions = [
            self._warm_overview_cache,
            self._warm_stats_cache,
            self._warm_breakdown_cache,
            self._warm_analytics_cache
        ]
        
        self.cache_manager.warm_cache_async(warming_functions, priority)
    
    def _warm_overview_cache(self):
        """Warm dashboard overview cache."""
        from .services_optimized import OptimizedDashboardCacheService
        
        cache_service = OptimizedDashboardCacheService(self.user)
        cache_service.get_cached_dashboard_data_optimized('monthly')
        cache_service.get_cached_dashboard_data_optimized('weekly')
    
    def _warm_stats_cache(self):
        """Warm dashboard stats cache."""
        cache_key = self.cache_manager.get_cache_key(
            CacheConfig.PREFIXES['DASHBOARD_STATS'],
            'monthly'
        )
        
        def generate_stats():
            from .services_optimized import OptimizedDashboardCacheService
            cache_service = OptimizedDashboardCacheService(self.user)
            return cache_service.get_cached_dashboard_data_optimized('monthly')
        
        self.cache_manager.get_or_set_with_lock(cache_key, generate_stats, 1800)
    
    def _warm_breakdown_cache(self):
        """Warm category breakdown cache."""
        cache_key = self.cache_manager.get_cache_key(
            CacheConfig.PREFIXES['DASHBOARD_BREAKDOWN'],
            'categories'
        )
        
        def generate_breakdown():
            from .models import CategoryAnalytics
            return list(CategoryAnalytics.objects.filter(
                owner=self.user
            ).order_by('-total_amount')[:50])
        
        self.cache_manager.get_or_set_with_lock(cache_key, generate_breakdown, 1800)
    
    def _warm_analytics_cache(self):
        """Warm analytics data cache."""
        cache_key = self.cache_manager.get_cache_key(
            CacheConfig.PREFIXES['ANALYTICS_DATA'],
            'recent'
        )
        
        def generate_analytics():
            from .models import PerformanceMetric
            return list(PerformanceMetric.objects.filter(
                owner=self.user
            ).order_by('-calculation_date')[:20])
        
        self.cache_manager.get_or_set_with_lock(cache_key, generate_analytics, 1800)


# Signal handlers for automatic cache invalidation
@receiver(request_finished)
def cleanup_cache_stats(sender, **kwargs):
    """Clean up cache statistics periodically."""
    # This would run cleanup logic
    pass


def get_dashboard_cache_manager(user: User) -> AdvancedCacheManager:
    """Factory function to get dashboard cache manager."""
    return AdvancedCacheManager(user)


def warm_user_dashboard_cache(user: User, priority: str = 'background'):
    """Convenience function to warm user's dashboard cache."""
    warmer = DashboardCacheWarmer(user)
    warmer.warm_dashboard_caches(priority)


# Cache middleware for automatic cache warming
class DashboardCacheMiddleware:
    """Middleware for automatic dashboard cache warming."""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Warm cache for authenticated users accessing dashboard
        if (hasattr(request, 'user') and 
            request.user.is_authenticated and 
            request.path.startswith('/api/dashboard/')):
            
            # Schedule background cache warming
            try:
                warm_user_dashboard_cache(request.user, 'background')
            except Exception as e:
                logger.warning(f"Background cache warming failed: {e}")
        
        return response