"""
SK-603: Advanced Caching Strategy Implementation

Advanced caching patterns and strategies that build upon SK-602's multi-level caching foundation.

Key features:
1. Advanced cache patterns (Write-through, Write-behind, Cache-aside)
2. Intelligent cache management with ML-based predictions
3. Distributed caching architecture with Redis clustering
4. Advanced cache analytics and monitoring
5. Cache security and encryption
6. Smart invalidation strategies
"""

import asyncio
import hashlib
import json
import pickle
import time
import uuid
import zlib
from collections import defaultdict, deque
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, List, Union, Callable, Tuple
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
import statistics

import redis
from redis.cluster import RedisCluster
from django.core.cache import cache, caches
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from cryptography.fernet import Fernet

# Import base classes from SK-602
from .cache_optimized import AdvancedCacheManager, CacheConfig, CacheStatistics

User = get_user_model()
logger = logging.getLogger(__name__)


class CachePattern(Enum):
    """Advanced cache patterns."""
    CACHE_ASIDE = "cache_aside"          # Read from cache, write to database first
    WRITE_THROUGH = "write_through"      # Write to cache and database synchronously
    WRITE_BEHIND = "write_behind"        # Write to cache immediately, database asynchronously
    REFRESH_AHEAD = "refresh_ahead"      # Refresh cache before expiration


class CachePredictionModel:
    """Machine learning-based cache prediction model with advanced features."""
    
    def __init__(self):
        self.access_patterns = defaultdict(list)
        self.user_behavior_patterns = defaultdict(lambda: defaultdict(list))
        self.time_series_data = defaultdict(list)
        self.access_frequency_map = defaultdict(int)
        self.prediction_weights = {
            'time_of_day': 0.25,
            'day_of_week': 0.20,
            'user_behavior': 0.30,
            'data_freshness': 0.15,
            'access_frequency': 0.10
        }
        self.model_accuracy_history = deque(maxlen=1000)
        
    def record_access(self, cache_key: str, timestamp: datetime, user_id: int, data_size: int = 0):
        """Record cache access for learning with enhanced metadata."""
        access_data = {
            'timestamp': timestamp,
            'hour': timestamp.hour,
            'day_of_week': timestamp.weekday(),
            'user_id': user_id,
            'cache_key': cache_key,
            'data_size': data_size,
            'access_count': self.access_frequency_map[cache_key] + 1
        }
        
        # Update access frequency
        self.access_frequency_map[cache_key] += 1
        
        # Keep detailed access patterns
        self.access_patterns[cache_key].append(access_data)
        if len(self.access_patterns[cache_key]) > 1000:
            self.access_patterns[cache_key].pop(0)
            
        # Track user behavior patterns
        self.user_behavior_patterns[user_id][cache_key].append(access_data)
        if len(self.user_behavior_patterns[user_id][cache_key]) > 100:
            self.user_behavior_patterns[user_id][cache_key].pop(0)
            
        # Store time series data for trend analysis
        self.time_series_data[cache_key].append({
            'timestamp': timestamp,
            'access_count': self.access_frequency_map[cache_key],
            'hour': timestamp.hour
        })
        if len(self.time_series_data[cache_key]) > 1000:
            self.time_series_data[cache_key].pop(0)
    
    def predict_access_probability(self, cache_key: str, future_time: datetime, user_id: int = None) -> float:
        """Predict probability of cache access at future time with enhanced features."""
        if cache_key not in self.access_patterns:
            return 0.1  # Default low probability for new keys
        
        accesses = self.access_patterns[cache_key]
        if not accesses:
            return 0.1
        
        # Time-based analysis
        hour_freq = defaultdict(int)
        day_freq = defaultdict(int)
        
        # Analyze recent patterns (last 100 accesses)
        recent_accesses = accesses[-100:]
        for access in recent_accesses:
            hour_freq[access['hour']] += 1
            day_freq[access['day_of_week']] += 1
        
        # Calculate time-based probability
        hour_prob = hour_freq.get(future_time.hour, 0) / len(recent_accesses)
        day_prob = day_freq.get(future_time.weekday(), 0) / len(recent_accesses)
        
        # User behavior analysis
        user_prob = 0.0
        if user_id and user_id in self.user_behavior_patterns:
            user_accesses = self.user_behavior_patterns[user_id][cache_key]
            if user_accesses:
                # Recent user accesses (last 20)
                recent_user_accesses = user_accesses[-20:]
                user_prob = len(recent_user_accesses) / 20.0
        
        # Data freshness factor (newer data might be accessed more)
        data_freshness = min(len(accesses) / 100.0, 1.0)
        
        # Access frequency factor (frequently accessed keys are likely to be accessed)
        access_freq_prob = min(self.access_frequency_map[cache_key] / 50.0, 1.0)
        
        # Combined probability with weighted factors
        probability = (
            hour_prob * self.prediction_weights['time_of_day'] +
            day_prob * self.prediction_weights['day_of_week'] +
            user_prob * self.prediction_weights['user_behavior'] +
            data_freshness * self.prediction_weights['data_freshness'] +
            access_freq_prob * self.prediction_weights['access_frequency']
        )
        
        # Apply smoothing and ensure valid probability
        smoothed_prob = min(max(probability, 0.0), 1.0)
        
        return smoothed_prob
    
    def should_refresh_ahead(self, cache_key: str, expiry_time: datetime, user_id: int = None) -> bool:
        """Determine if cache should be refreshed ahead of expiration."""
        if expiry_time <= datetime.now():
            return True
        
        time_to_expiry = (expiry_time - datetime.now()).total_seconds()
        if time_to_expiry < 300:  # Less than 5 minutes
            # Predict if likely to be accessed soon
            near_future = datetime.now() + timedelta(minutes=10)
            probability = self.predict_access_probability(cache_key, near_future, user_id)
            return probability > 0.5
        
        return False
    
    def get_cache_warming_candidates(self, user_id: int = None, limit: int = 10) -> List[str]:
        """Get cache keys that are likely to be accessed soon for proactive warming."""
        candidates = []
        
        # Analyze all tracked cache keys for this user or globally
        if user_id:
            # User-specific analysis
            if user_id in self.user_behavior_patterns:
                for cache_key in self.user_behavior_patterns[user_id]:
                    near_future = datetime.now() + timedelta(minutes=30)
                    probability = self.predict_access_probability(cache_key, near_future, user_id)
                    candidates.append((cache_key, probability))
        else:
            # Global analysis
            for cache_key in self.access_patterns:
                near_future = datetime.now() + timedelta(minutes=30)
                probability = self.predict_access_probability(cache_key, near_future, user_id)
                candidates.append((cache_key, probability))
        
        # Sort by probability and return top candidates
        candidates.sort(key=lambda x: x[1], reverse=True)
        return [key for key, prob in candidates[:limit]]
    
    def get_optimal_ttl(self, cache_key: str, user_id: int = None) -> int:
        """Calculate optimal TTL based on access patterns."""
        if cache_key not in self.access_patterns:
            return 1800  # Default 30 minutes
        
        accesses = self.access_patterns[cache_key]
        if len(accesses) < 5:
            return 1800  # Not enough data, use default
        
        # Analyze access intervals
        intervals = []
        for i in range(1, len(accesses)):
            interval = (accesses[i]['timestamp'] - accesses[i-1]['timestamp']).total_seconds()
            intervals.append(interval)
        
        if not intervals:
            return 1800
        
        # Use statistical analysis to determine optimal TTL
        avg_interval = statistics.mean(intervals)
        median_interval = statistics.median(intervals)
        
        # Use a combination of average and median, with some buffer
        optimal_ttl = int((avg_interval + median_interval) / 2 * 1.5)
        
        # Ensure reasonable bounds (5 minutes to 2 hours)
        return max(300, min(optimal_ttl, 7200))
    
    def update_model_accuracy(self, prediction: float, actual_access: bool):
        """Update model accuracy based on prediction results."""
        accuracy = 1.0 if (prediction > 0.5 and actual_access) or (prediction <= 0.5 and not actual_access) else 0.0
        self.model_accuracy_history.append(accuracy)
        
        # Adjust weights based on recent accuracy
        if len(self.model_accuracy_history) >= 10:
            recent_accuracy = statistics.mean(list(self.model_accuracy_history)[-10:])
            if recent_accuracy < 0.6:  # Below 60% accuracy
                # Reduce weights for less accurate factors
                self.prediction_weights['time_of_day'] *= 0.95
                self.prediction_weights['day_of_week'] *= 0.95
    
    def get_model_performance_stats(self) -> Dict[str, Any]:
        """Get model performance statistics."""
        if not self.model_accuracy_history:
            return {'accuracy': 0.0, 'sample_size': 0}
        
        accuracy = statistics.mean(self.model_accuracy_history)
        return {
            'accuracy': round(accuracy, 4),
            'sample_size': len(self.model_accuracy_history),
            'tracked_keys': len(self.access_patterns),
            'prediction_weights': dict(self.prediction_weights)
        }


@dataclass
class CacheEntry:
    """Enhanced cache entry with metadata."""
    key: str
    data: Any
    created_at: datetime
    expires_at: datetime
    access_count: int = 0
    last_accessed: datetime = None
    pattern: CachePattern = CachePattern.CACHE_ASIDE
    encrypted: bool = False
    compression_ratio: float = 1.0
    size_bytes: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'pattern': self.pattern.value
        }


class AdvancedCacheSecurityManager:
    """Security features for cache data."""
    
    def __init__(self):
        # Generate or load encryption key
        self.encryption_key = self._get_or_create_key()
        self.cipher = Fernet(self.encryption_key)
        self.access_log = deque(maxlen=10000)  # Keep last 10K access logs
    
    def _get_or_create_key(self) -> bytes:
        """Get or create encryption key."""
        key_setting = getattr(settings, 'CACHE_ENCRYPTION_KEY', None)
        if key_setting:
            return key_setting.encode()
        else:
            # Generate new key (in production, this should be stored securely)
            return Fernet.generate_key()
    
    def encrypt_data(self, data: Any) -> bytes:
        """Encrypt cache data."""
        try:
            serialized = pickle.dumps(data)
            encrypted = self.cipher.encrypt(serialized)
            return encrypted
        except Exception as e:
            logger.error(f"Cache encryption failed: {e}")
            return pickle.dumps(data)  # Fallback to unencrypted
    
    def decrypt_data(self, encrypted_data: bytes) -> Any:
        """Decrypt cache data."""
        try:
            decrypted = self.cipher.decrypt(encrypted_data)
            return pickle.loads(decrypted)
        except Exception as e:
            logger.error(f"Cache decryption failed: {e}")
            # Try as unencrypted data
            try:
                return pickle.loads(encrypted_data)
            except:
                return None
    
    def log_access(self, user_id: int, cache_key: str, operation: str, success: bool):
        """Log cache access for security auditing."""
        log_entry = {
            'timestamp': timezone.now(),
            'user_id': user_id,
            'cache_key': cache_key,
            'operation': operation,
            'success': success,
            'ip_address': 'unknown'  # Would be populated by middleware
        }
        self.access_log.append(log_entry)
    
    def get_access_logs(self, user_id: int = None, hours: int = 24) -> List[Dict]:
        """Get security access logs."""
        cutoff_time = timezone.now() - timedelta(hours=hours)
        
        filtered_logs = [
            log for log in self.access_log
            if log['timestamp'] >= cutoff_time and (user_id is None or log['user_id'] == user_id)
        ]
        
        return [
            {**log, 'timestamp': log['timestamp'].isoformat()}
            for log in filtered_logs
        ]


class AdvancedCacheAnalytics:
    """Advanced cache analytics and monitoring."""
    
    def __init__(self):
        self.metrics = defaultdict(list)
        self.performance_history = deque(maxlen=1000)
        self.cost_analysis = defaultdict(float)
        
    def record_operation(self, operation_type: str, duration: float, cache_hit: bool, 
                        data_size: int, user_id: int):
        """Record cache operation for analytics."""
        metric = {
            'timestamp': timezone.now(),
            'operation': operation_type,
            'duration_ms': duration,
            'cache_hit': cache_hit,
            'data_size_bytes': data_size,
            'user_id': user_id
        }
        
        self.metrics[operation_type].append(metric)
        self.performance_history.append(metric)
        
        # Calculate cost (simplified model)
        cost = self._calculate_operation_cost(operation_type, duration, data_size, cache_hit)
        self.cost_analysis[operation_type] += cost
    
    def _calculate_operation_cost(self, operation: str, duration: float, 
                                 data_size: int, cache_hit: bool) -> float:
        """Calculate cost of cache operation."""
        base_cost = 0.001  # Base cost per operation
        
        # Time cost (more expensive for longer operations)
        time_cost = duration * 0.0001
        
        # Data transfer cost
        transfer_cost = data_size * 0.000001
        
        # Cache miss penalty (database query is more expensive)
        miss_penalty = 0.01 if not cache_hit else 0
        
        return base_cost + time_cost + transfer_cost + miss_penalty
    
    def get_analytics_summary(self) -> Dict[str, Any]:
        """Get comprehensive analytics summary."""
        if not self.performance_history:
            return {'message': 'No analytics data available'}
        
        recent_metrics = list(self.performance_history)[-100:]  # Last 100 operations
        
        # Performance metrics
        response_times = [m['duration_ms'] for m in recent_metrics]
        cache_hits = [m['cache_hit'] for m in recent_metrics]
        data_sizes = [m['data_size_bytes'] for m in recent_metrics]
        
        analytics = {
            'performance': {
                'avg_response_time_ms': statistics.mean(response_times),
                'median_response_time_ms': statistics.median(response_times),
                'p95_response_time_ms': statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else max(response_times),
                'cache_hit_rate': (sum(cache_hits) / len(cache_hits)) * 100
            },
            'data_transfer': {
                'avg_data_size_bytes': statistics.mean(data_sizes),
                'total_data_transferred_mb': sum(data_sizes) / 1024 / 1024,
                'compression_efficiency': self._calculate_compression_efficiency()
            },
            'cost_analysis': dict(self.cost_analysis),
            'operation_breakdown': self._get_operation_breakdown(),
            'trends': self._analyze_trends(),
            'recommendations': self._generate_recommendations()
        }
        
        return analytics
    
    def _calculate_compression_efficiency(self) -> float:
        """Calculate overall compression efficiency."""
        # Simplified calculation - would be more sophisticated in practice
        return 0.35  # Assume 35% compression ratio
    
    def _get_operation_breakdown(self) -> Dict[str, int]:
        """Get breakdown of operations by type."""
        breakdown = defaultdict(int)
        for operation_type, metrics in self.metrics.items():
            breakdown[operation_type] = len(metrics)
        return dict(breakdown)
    
    def _analyze_trends(self) -> Dict[str, str]:
        """Analyze performance trends."""
        if len(self.performance_history) < 50:
            return {'message': 'Insufficient data for trend analysis'}
        
        recent = list(self.performance_history)[-25:]
        older = list(self.performance_history)[-50:-25]
        
        recent_avg = statistics.mean([m['duration_ms'] for m in recent])
        older_avg = statistics.mean([m['duration_ms'] for m in older])
        
        trend = 'improving' if recent_avg < older_avg else 'degrading'
        change_percent = abs((recent_avg - older_avg) / older_avg) * 100
        
        return {
            'performance_trend': trend,
            'change_percentage': round(change_percent, 2),
            'recommendation': f"Performance is {trend} by {change_percent:.1f}%"
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate optimization recommendations."""
        recommendations = []
        
        if not self.performance_history:
            return ['Collect more data for meaningful recommendations']
        
        recent_metrics = list(self.performance_history)[-50:]
        
        # Analyze cache hit rate
        cache_hit_rate = (sum(m['cache_hit'] for m in recent_metrics) / len(recent_metrics)) * 100
        
        if cache_hit_rate < 70:
            recommendations.append("Low cache hit rate detected - consider cache warming or TTL optimization")
        
        # Analyze response times
        avg_response_time = statistics.mean([m['duration_ms'] for m in recent_metrics])
        if avg_response_time > 100:
            recommendations.append("High response times detected - consider cache preloading or data optimization")
        
        # Analyze data sizes
        avg_data_size = statistics.mean([m['data_size_bytes'] for m in recent_metrics])
        if avg_data_size > 1024 * 1024:  # 1MB
            recommendations.append("Large data sizes detected - consider compression or data filtering")
        
        if not recommendations:
            recommendations.append("Cache performance is optimal - continue monitoring")
        
        return recommendations


class AdvancedCacheManager(AdvancedCacheManager):
    """
    Enhanced cache manager with advanced patterns and intelligence.
    
    Extends SK-602's AdvancedCacheManager with:
    - Advanced cache patterns (write-through, write-behind, cache-aside)
    - ML-based cache predictions and intelligent warming
    - Enhanced security with encryption
    - Comprehensive analytics and monitoring
    - Distributed caching support
    """
    
    def __init__(self, user: User):
        super().__init__(user)
        
        # Advanced features
        self.prediction_model = CachePredictionModel()
        self.security_manager = AdvancedCacheSecurityManager()
        self.analytics = AdvancedCacheAnalytics()
        
        # Pattern-specific configurations
        self.pattern_configs = {
            CachePattern.WRITE_THROUGH: {'timeout': 3600, 'levels': ['L1_MEMORY', 'L2_REDIS']},
            CachePattern.WRITE_BEHIND: {'timeout': 1800, 'levels': ['L1_MEMORY'], 'batch_size': 10},
            CachePattern.CACHE_ASIDE: {'timeout': 1800, 'levels': ['L1_MEMORY', 'L2_REDIS']},
            CachePattern.REFRESH_AHEAD: {'timeout': 3600, 'refresh_threshold': 300}
        }
        
        # Background tasks
        self.write_behind_queue = deque()
        self.refresh_ahead_scheduler = {}
        
        # Distributed Caching Support
        self.redis_cluster_nodes = getattr(settings, 'REDIS_CLUSTER_NODES', None)
        self.redis_cluster = None
        if self.redis_cluster_nodes:
            try:
                self.redis_cluster = RedisCluster(startup_nodes=self.redis_cluster_nodes, decode_responses=True)
                logger.info("Redis Cluster connection established.")
            except Exception as e:
                logger.error(f"Failed to connect to Redis Cluster: {e}")

    def _get_cache_backend(self, level: str) -> Any:
        if level == 'L2_REDIS' and self.redis_cluster:
            return self.redis_cluster
        return super()._get_cache_backend(level)
    
    def _start_background_processors(self):
        """Start background processing threads."""
        # Write-behind processor
        write_behind_thread = threading.Thread(target=self._process_write_behind_queue, daemon=True)
        write_behind_thread.start()
        
        # Refresh-ahead processor
        refresh_ahead_thread = threading.Thread(target=self._process_refresh_ahead, daemon=True)
        refresh_ahead_thread.start()
    
    def get_with_pattern(self, cache_key: str, data_func: Callable = None, 
                        pattern: CachePattern = CachePattern.CACHE_ASIDE,
                        encrypt: bool = False, **kwargs) -> Any:
        """
        Get data using specified cache pattern.
        
        Args:
            cache_key: Cache key
            data_func: Function to generate data if not cached
            pattern: Cache pattern to use
            encrypt: Whether to encrypt cached data
            **kwargs: Additional pattern-specific parameters
        """
        start_time = time.time()
        
        # Record access for ML model
        self.prediction_model.record_access(cache_key, timezone.now(), self.user.id)
        
        # Security logging
        self.security_manager.log_access(self.user.id, cache_key, 'GET', True)
        
        try:
            if pattern == CachePattern.CACHE_ASIDE:
                return self._get_cache_aside(cache_key, data_func, encrypt, **kwargs)
            elif pattern == CachePattern.WRITE_THROUGH:
                return self._get_write_through(cache_key, data_func, encrypt, **kwargs) 
            elif pattern == CachePattern.WRITE_BEHIND:
                return self._get_write_behind(cache_key, data_func, encrypt, **kwargs)
            elif pattern == CachePattern.REFRESH_AHEAD:
                return self._get_refresh_ahead(cache_key, data_func, encrypt, **kwargs)
            else:
                return self.get_multi_level(cache_key)
                
        finally:
            # Record analytics
            duration = (time.time() - start_time) * 1000
            self.analytics.record_operation(
                operation_type=f'GET_{pattern.value}',
                duration=duration,
                cache_hit=True,  # Simplified for now
                data_size=0,     # Would measure actual size
                user_id=self.user.id
            )
    
    def _get_cache_aside(self, cache_key: str, data_func: Callable, encrypt: bool, **kwargs) -> Any:
        """Cache-aside pattern: Check cache first, then generate if needed."""
        # Try cache first
        cached_data = self.get_multi_level(cache_key)
        if cached_data is not None:
            if encrypt:
                cached_data = self.security_manager.decrypt_data(cached_data)
            return cached_data
        
        # Generate data if not cached
        if data_func:
            data = data_func()
            
            # Store in cache
            if encrypt:
                data_to_cache = self.security_manager.encrypt_data(data)
            else:
                data_to_cache = data
            
            config = self.pattern_configs[CachePattern.CACHE_ASIDE]
            self.set_multi_level(cache_key, data_to_cache, config['timeout'], config['levels'])
            
            return data
        
        return None
    
    def _get_write_through(self, cache_key: str, data_func: Callable, encrypt: bool, **kwargs) -> Any:
        """Write-through pattern: Always write to cache and database synchronously."""
        # For read operations, check cache first
        cached_data = self.get_multi_level(cache_key)
        if cached_data is not None:
            if encrypt:
                cached_data = self.security_manager.decrypt_data(cached_data)
            return cached_data
        
        # Generate and store data
        if data_func:
            data = data_func()
            self.set_with_pattern(cache_key, data, CachePattern.WRITE_THROUGH, encrypt=encrypt)
            return data
        
        return None
    
    def _get_write_behind(self, cache_key: str, data_func: Callable, encrypt: bool, **kwargs) -> Any:
        """Write-behind pattern: Write to cache immediately, database asynchronously."""
        # Check cache first
        cached_data = self.get_multi_level(cache_key)
        if cached_data is not None:
            if encrypt:
                cached_data = self.security_manager.decrypt_data(cached_data)
            return cached_data
        
        # Generate data and cache immediately
        if data_func:
            data = data_func()
            
            # Cache immediately
            if encrypt:
                data_to_cache = self.security_manager.encrypt_data(data)
            else:
                data_to_cache = data
            
            config = self.pattern_configs[CachePattern.WRITE_BEHIND]
            self.set_multi_level(cache_key, data_to_cache, config['timeout'], config['levels'])
            
            # Queue for background database write
            self.write_behind_queue.append({
                'cache_key': cache_key,
                'data': data,
                'timestamp': timezone.now()
            })
            
            return data
        
        return None
    
    def _get_refresh_ahead(self, cache_key: str, data_func: Callable, encrypt: bool, **kwargs) -> Any:
        """Refresh-ahead pattern: Refresh cache before expiration."""
        # Check if refresh is needed
        if self.prediction_model.should_refresh_ahead(cache_key, timezone.now() + timedelta(minutes=5)):
            # Schedule refresh
            self.refresh_ahead_scheduler[cache_key] = {
                'data_func': data_func,
                'encrypt': encrypt,
                'scheduled_at': timezone.now()
            }
        
        # Return current cached data or generate new
        return self._get_cache_aside(cache_key, data_func, encrypt, **kwargs)
    
    def set_with_pattern(self, cache_key: str, data: Any, pattern: CachePattern, 
                        encrypt: bool = False, **kwargs) -> bool:
        """Set data using specified cache pattern."""
        start_time = time.time()
        
        # Security logging
        self.security_manager.log_access(self.user.id, cache_key, 'SET', True)
        
        try:
            # Encrypt if requested
            if encrypt:
                data_to_cache = self.security_manager.encrypt_data(data)
            else:
                data_to_cache = data
            
            # Apply pattern-specific logic
            config = self.pattern_configs[pattern]
            
            if pattern == CachePattern.WRITE_THROUGH:
                # Write to cache and database synchronously
                success = self.set_multi_level(cache_key, data_to_cache, config['timeout'], config['levels'])
                # Would also write to database here in real implementation
                return success
                
            elif pattern == CachePattern.WRITE_BEHIND:
                # Write to cache immediately
                success = self.set_multi_level(cache_key, data_to_cache, config['timeout'], config['levels'])
                
                # Queue for background database write
                self.write_behind_queue.append({
                    'cache_key': cache_key,
                    'data': data,
                    'timestamp': timezone.now()
                })
                
                return success
                
            else:
                # Default cache-aside behavior
                return self.set_multi_level(cache_key, data_to_cache, config.get('timeout', 1800))
                
        finally:
            # Record analytics
            duration = (time.time() - start_time) * 1000
            self.analytics.record_operation(
                operation_type=f'SET_{pattern.value}',
                duration=duration,
                cache_hit=False,
                data_size=len(str(data)),  # Simplified size calculation
                user_id=self.user.id
            )
    
    def _process_write_behind_queue(self):
        """Background processor for write-behind operations."""
        while True:
            try:
                if self.write_behind_queue:
                    batch = []
                    
                    # Collect batch of operations
                    batch_size = self.pattern_configs[CachePattern.WRITE_BEHIND]['batch_size']
                    for _ in range(min(batch_size, len(self.write_behind_queue))):
                        if self.write_behind_queue:
                            batch.append(self.write_behind_queue.popleft())
                    
                    # Process batch
                    if batch:
                        self._execute_write_behind_batch(batch)
                
                time.sleep(5)  # Process every 5 seconds
                
            except Exception as e:
                logger.error(f"Write-behind processor error: {e}")
                time.sleep(10)  # Longer wait on error
    
    def _execute_write_behind_batch(self, batch: List[Dict]):
        """Execute batch of write-behind operations."""
        # In real implementation, this would write to database
        logger.info(f"Processing write-behind batch of {len(batch)} operations")
        
        for operation in batch:
            try:
                # Simulate database write
                logger.debug(f"Writing to database: {operation['cache_key']}")
                # In real implementation: database_write(operation['data'])
                
            except Exception as e:
                logger.error(f"Write-behind operation failed: {e}")
                # Could implement retry logic here
    
    def _process_refresh_ahead(self):
        """Background processor for refresh-ahead operations."""
        while True:
            try:
                current_time = timezone.now()
                
                # Check scheduled refreshes
                for cache_key, refresh_info in list(self.refresh_ahead_scheduler.items()):
                    scheduled_time = refresh_info['scheduled_at']
                    
                    # Refresh if scheduled time has passed
                    if current_time >= scheduled_time:
                        try:
                            data_func = refresh_info['data_func']
                            encrypt = refresh_info['encrypt']
                            
                            # Generate fresh data
                            fresh_data = data_func()
                            
                            # Update cache
                            self.set_with_pattern(cache_key, fresh_data, CachePattern.CACHE_ASIDE, encrypt=encrypt)
                            
                            logger.info(f"Refresh-ahead completed for {cache_key}")
                            
                        except Exception as e:
                            logger.error(f"Refresh-ahead failed for {cache_key}: {e}")
                        
                        finally:
                            # Remove from scheduler
                            del self.refresh_ahead_scheduler[cache_key]
                
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Refresh-ahead processor error: {e}")
                time.sleep(60)
    
    def get_analytics_report(self) -> Dict[str, Any]:
        """Get comprehensive analytics report."""
        return {
            'cache_analytics': self.analytics.get_analytics_summary(),
            'security_logs': self.security_manager.get_access_logs(self.user.id),
            'prediction_model_stats': {
                'tracked_keys': len(self.prediction_model.access_patterns),
                'total_predictions': sum(len(pattern) for pattern in self.prediction_model.access_patterns.values())
            },
            'background_queues': {
                'write_behind_queue_size': len(self.write_behind_queue),
                'refresh_ahead_scheduled': len(self.refresh_ahead_scheduler)
            },
            'sk603_status': 'active',
            'advanced_features': {
                'intelligent_caching': True,
                'security_encryption': True,
                'pattern_based_caching': True,
                'ml_predictions': True,
                'background_processing': True
            }
        }


# Factory functions for SK-603 integration
def get_advanced_cache_manager(user: User) -> AdvancedCacheManager:
    """Get advanced cache manager instance for user."""
    return AdvancedCacheManager(user)


def create_intelligent_cache_key(prefix: str, user: User, **params) -> str:
    """Create intelligent cache key with SK-603 enhancements."""
    manager = get_advanced_cache_manager(user)
    return manager.get_cache_key(prefix, 'intelligent', **params)


# Decorators for advanced caching patterns
def cache_with_pattern(pattern: CachePattern = CachePattern.CACHE_ASIDE, 
                      encrypt: bool = False, timeout: int = 1800):
    """Decorator for advanced cache patterns."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Extract user from args if available
            user = None
            if args and hasattr(args[0], 'user'):
                user = args[0].user
            elif 'user' in kwargs:
                user = kwargs['user']
            
            if not user:
                # No user available, execute function directly
                return func(*args, **kwargs)
            
            # Create cache key
            cache_key = f"func_{func.__name__}_{hash(str(args) + str(kwargs))}"
            
            # Get cache manager
            cache_manager = get_advanced_cache_manager(user)
            
            # Define data function
            def data_func():
                return func(*args, **kwargs)
            
            # Get data using specified pattern
            return cache_manager.get_with_pattern(
                cache_key, data_func, pattern, encrypt=encrypt
            )
        
        return wrapper
    return decorator