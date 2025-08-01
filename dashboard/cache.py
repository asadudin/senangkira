"""
Dashboard caching utilities and strategies.
Optimizes dashboard performance through intelligent caching.
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from decimal import Decimal

from django.core.cache import cache
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import QuerySet

User = get_user_model()


class DashboardCache:
    """
    Centralized dashboard caching system with intelligent invalidation.
    Provides multiple caching strategies and automatic cache management.
    """
    
    # Cache key prefixes
    OVERVIEW_KEY = "dashboard_overview"
    STATS_KEY = "dashboard_stats"
    TRENDS_KEY = "dashboard_trends"
    BREAKDOWN_KEY = "dashboard_breakdown"
    KPI_KEY = "dashboard_kpi"
    CLIENT_KEY = "dashboard_client"
    SNAPSHOT_KEY = "dashboard_snapshot"
    
    # Default cache timeouts (in seconds)
    DEFAULT_TIMEOUT = 1800  # 30 minutes
    STATS_TIMEOUT = 300     # 5 minutes
    TRENDS_TIMEOUT = 3600   # 1 hour
    OVERVIEW_TIMEOUT = 1800 # 30 minutes
    
    def __init__(self, user: User):
        self.user = user
        self.user_prefix = f"user_{user.id}"
    
    def get_cache_key(self, key_type: str, **params) -> str:
        """
        Generate cache key with user context and parameters.
        
        Args:
            key_type: Type of cache key (overview, stats, etc.)
            **params: Additional parameters to include in key
            
        Returns:
            str: Generated cache key
        """
        # Create parameter hash for complex parameters
        if params:
            param_str = json.dumps(params, sort_keys=True, cls=DjangoJSONEncoder)
            param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
            return f"{self.user_prefix}_{key_type}_{param_hash}"
        
        return f"{self.user_prefix}_{key_type}"
    
    def get_cached_data(self, key_type: str, **params) -> Optional[Dict[str, Any]]:
        """
        Get cached data with automatic key generation.
        
        Args:
            key_type: Type of cached data
            **params: Parameters used to generate cache key
            
        Returns:
            Cached data or None if not found/expired
        """
        cache_key = self.get_cache_key(key_type, **params)
        return cache.get(cache_key)
    
    def set_cached_data(self, key_type: str, data: Dict[str, Any], timeout: Optional[int] = None, **params) -> bool:
        """
        Cache data with automatic key generation and timeout.
        
        Args:
            key_type: Type of data being cached
            data: Data to cache
            timeout: Cache timeout in seconds (uses default if None)
            **params: Parameters used to generate cache key
            
        Returns:
            bool: True if successfully cached
        """
        if timeout is None:
            timeout = self._get_default_timeout(key_type)
        
        cache_key = self.get_cache_key(key_type, **params)
        
        # Add metadata to cached data
        cached_data = {
            'data': data,
            'cached_at': timezone.now().isoformat(),
            'cache_key': cache_key,
            'timeout': timeout
        }
        
        return cache.set(cache_key, cached_data, timeout)
    
    def invalidate_cache(self, key_type: Optional[str] = None, **params) -> bool:
        """
        Invalidate cached data.
        
        Args:
            key_type: Specific type to invalidate (or None for all user cache)
            **params: Parameters for specific cache key
            
        Returns:
            bool: True if invalidation succeeded
        """
        if key_type:
            # Invalidate specific cache key
            cache_key = self.get_cache_key(key_type, **params)
            return cache.delete(cache_key)
        
        # Invalidate all user cache (pattern-based, implementation-dependent)
        # This is a simplified approach - in production, use Redis pattern deletion
        key_types = [
            self.OVERVIEW_KEY, self.STATS_KEY, self.TRENDS_KEY,
            self.BREAKDOWN_KEY, self.KPI_KEY, self.CLIENT_KEY, self.SNAPSHOT_KEY
        ]
        
        success = True
        for kt in key_types:
            cache_key = self.get_cache_key(kt)
            success &= cache.delete(cache_key)
        
        return success
    
    def get_or_set(self, key_type: str, data_func, timeout: Optional[int] = None, **params) -> Dict[str, Any]:
        """
        Get cached data or execute function and cache result.
        
        Args:
            key_type: Type of cached data
            data_func: Function to call if cache miss
            timeout: Cache timeout
            **params: Cache key parameters
            
        Returns:
            Data from cache or function result
        """
        cached_data = self.get_cached_data(key_type, **params)
        
        if cached_data is not None:
            return cached_data.get('data', cached_data)
        
        # Cache miss - execute function and cache result
        data = data_func()
        self.set_cached_data(key_type, data, timeout, **params)
        
        return data
    
    def _get_default_timeout(self, key_type: str) -> int:
        """Get default timeout for cache key type."""
        timeout_map = {
            self.OVERVIEW_KEY: self.OVERVIEW_TIMEOUT,
            self.STATS_KEY: self.STATS_TIMEOUT,
            self.TRENDS_KEY: self.TRENDS_TIMEOUT,
            self.BREAKDOWN_KEY: self.DEFAULT_TIMEOUT,
            self.KPI_KEY: self.DEFAULT_TIMEOUT,
            self.CLIENT_KEY: self.DEFAULT_TIMEOUT,
            self.SNAPSHOT_KEY: self.DEFAULT_TIMEOUT,
        }
        
        return timeout_map.get(key_type, self.DEFAULT_TIMEOUT)


class QueryCache:
    """
    Database query caching for expensive dashboard operations.
    Caches QuerySet results and provides invalidation strategies.
    """
    
    def __init__(self, user: User):
        self.user = user
        self.cache = DashboardCache(user)
    
    def cache_queryset(self, queryset: QuerySet, cache_key: str, timeout: int = 1800) -> List[Dict]:
        """
        Cache QuerySet results as serializable data.
        
        Args:
            queryset: Django QuerySet to cache
            cache_key: Cache key for the query
            timeout: Cache timeout in seconds
            
        Returns:
            List of model data dictionaries
        """
        # Convert QuerySet to list of dictionaries
        data = []
        for obj in queryset:
            if hasattr(obj, 'to_dict'):
                data.append(obj.to_dict())
            else:
                # Fallback to model_to_dict equivalent
                data.append(self._model_to_dict(obj))
        
        # Cache the data
        cache.set(f"query_{self.user.id}_{cache_key}", data, timeout)
        
        return data
    
    def get_cached_queryset(self, cache_key: str) -> Optional[List[Dict]]:
        """
        Get cached QuerySet results.
        
        Args:
            cache_key: Cache key for the query
            
        Returns:
            List of cached model data or None
        """
        return cache.get(f"query_{self.user.id}_{cache_key}")
    
    def invalidate_queryset_cache(self, cache_key: str) -> bool:
        """
        Invalidate cached QuerySet.
        
        Args:
            cache_key: Cache key to invalidate
            
        Returns:
            bool: True if invalidation succeeded
        """
        return cache.delete(f"query_{self.user.id}_{cache_key}")
    
    def _model_to_dict(self, instance) -> Dict[str, Any]:
        """Convert model instance to dictionary."""
        data = {}
        for field in instance._meta.fields:
            value = getattr(instance, field.name)
            
            # Handle special field types
            if isinstance(value, Decimal):
                data[field.name] = float(value)
            elif isinstance(value, datetime):
                data[field.name] = value.isoformat()
            elif hasattr(value, 'pk'):  # Foreign key
                data[field.name] = str(value.pk)
            else:
                data[field.name] = value
        
        return data


class CacheInvalidationManager:
    """
    Manages cache invalidation based on data changes.
    Provides hooks for model save/delete signals.
    """
    
    @classmethod
    def invalidate_user_dashboard_cache(cls, user: User, cache_types: Optional[List[str]] = None):
        """
        Invalidate dashboard cache for a specific user.
        
        Args:
            user: User whose cache to invalidate
            cache_types: Specific cache types to invalidate (None for all)
        """
        cache_manager = DashboardCache(user)
        
        if cache_types:
            for cache_type in cache_types:
                cache_manager.invalidate_cache(cache_type)
        else:
            cache_manager.invalidate_cache()
    
    @classmethod
    def on_expense_change(cls, user: User):
        """Handle cache invalidation when expense data changes."""
        cls.invalidate_user_dashboard_cache(user, [
            DashboardCache.OVERVIEW_KEY,
            DashboardCache.STATS_KEY,
            DashboardCache.BREAKDOWN_KEY
        ])
    
    @classmethod
    def on_invoice_change(cls, user: User):
        """Handle cache invalidation when invoice data changes."""
        cls.invalidate_user_dashboard_cache(user, [
            DashboardCache.OVERVIEW_KEY,
            DashboardCache.STATS_KEY,
            DashboardCache.CLIENT_KEY
        ])
    
    @classmethod
    def on_client_change(cls, user: User):
        """Handle cache invalidation when client data changes."""
        cls.invalidate_user_dashboard_cache(user, [
            DashboardCache.OVERVIEW_KEY,
            DashboardCache.CLIENT_KEY
        ])


class PerformanceOptimizer:
    """
    Dashboard performance optimization utilities.
    Provides query optimization and caching strategies.
    """
    
    def __init__(self, user: User):
        self.user = user
    
    def optimize_dashboard_queries(self) -> Dict[str, Any]:
        """
        Analyze and optimize dashboard queries.
        
        Returns:
            Dict with optimization recommendations
        """
        from .models import DashboardSnapshot, CategoryAnalytics, ClientAnalytics
        
        recommendations = {
            'query_optimizations': [],
            'index_recommendations': [],
            'cache_strategies': []
        }
        
        # Check if indexes are being used effectively
        recent_snapshots = DashboardSnapshot.objects.filter(
            owner=self.user
        ).count()
        
        if recent_snapshots > 100:
            recommendations['query_optimizations'].append(
                "Consider implementing data archiving for old snapshots"
            )
        
        # Check category analytics distribution
        category_count = CategoryAnalytics.objects.filter(owner=self.user).count()
        
        if category_count > 1000:
            recommendations['cache_strategies'].append(
                "Implement category-specific caching for large datasets"
            )
        
        # Check client analytics
        client_count = ClientAnalytics.objects.filter(owner=self.user).count()
        
        if client_count > 500:
            recommendations['query_optimizations'].append(
                "Consider pagination for client analytics views"
            )
        
        return recommendations
    
    def get_cache_hit_rate(self) -> Dict[str, float]:
        """
        Calculate cache hit rates for different dashboard components.
        
        Returns:
            Dict with hit rates by component
        """
        # This would require cache hit tracking in production
        # For now, return placeholder data
        return {
            'overview': 0.85,
            'stats': 0.92,
            'trends': 0.78,
            'breakdown': 0.81,
            'kpis': 0.88
        }
    
    def suggest_cache_warming(self) -> List[str]:
        """
        Suggest cache warming strategies based on usage patterns.
        
        Returns:
            List of cache warming recommendations
        """
        suggestions = []
        
        # Always warm overview cache
        suggestions.append("Warm overview cache during off-peak hours")
        
        # Check if user has many clients
        from .models import ClientAnalytics
        client_count = ClientAnalytics.objects.filter(owner=self.user).count()
        
        if client_count > 50:
            suggestions.append("Pre-warm client analytics cache")
        
        # Check if user has complex category breakdowns
        from .models import CategoryAnalytics
        category_count = CategoryAnalytics.objects.filter(owner=self.user).count()
        
        if category_count > 20:
            suggestions.append("Pre-calculate category breakdown data")
        
        return suggestions


def warm_dashboard_cache(user: User, cache_types: Optional[List[str]] = None) -> Dict[str, bool]:
    """
    Warm dashboard cache for a user.
    
    Args:
        user: User to warm cache for
        cache_types: Specific cache types to warm (None for all)
        
    Returns:
        Dict with warming results by cache type
    """
    from .services import DashboardCacheService
    
    cache_service = DashboardCacheService(user)
    results = {}
    
    try:
        # Force refresh to warm cache
        refresh_results = cache_service.refresh_dashboard_cache(force_refresh=True)
        results['refresh'] = refresh_results.get('refreshed', False)
        
        # Get cached data to ensure it's warm
        cached_data = cache_service.get_cached_dashboard_data()
        results['overview'] = cached_data is not None
        
        return results
        
    except Exception as e:
        return {'error': str(e), 'success': False}


def get_cache_statistics(user: User) -> Dict[str, Any]:
    """
    Get cache statistics for a user's dashboard.
    
    Args:
        user: User to get statistics for
        
    Returns:
        Dict with cache statistics
    """
    cache_manager = DashboardCache(user)
    
    # Check which caches are active
    cache_status = {}
    cache_types = [
        'overview', 'stats', 'trends', 'breakdown', 'kpis', 'clients'
    ]
    
    for cache_type in cache_types:
        cached_data = cache_manager.get_cached_data(cache_type)
        cache_status[cache_type] = {
            'active': cached_data is not None,
            'cached_at': cached_data.get('cached_at') if cached_data else None
        }
    
    return {
        'user_id': user.id,
        'cache_status': cache_status,
        'total_active_caches': sum(1 for status in cache_status.values() if status['active']),
        'last_check': timezone.now().isoformat()
    }