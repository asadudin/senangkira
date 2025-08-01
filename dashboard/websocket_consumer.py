"""
WebSocket consumer for real-time dashboard updates.
Provides live dashboard data streaming via WebSocket connections.
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, Any

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.core.serializers.json import DjangoJSONEncoder

from .realtime import RealTimeDashboardAggregator

User = get_user_model()


class DashboardConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time dashboard data streaming.
    Provides live updates with configurable intervals and automatic reconnection.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.aggregator = None
        self.update_task = None
        self.room_group_name = None
        self.update_interval = 30  # Default 30 seconds
        
    async def connect(self):
        """Handle WebSocket connection."""
        # Get user from scope (requires authentication middleware)
        self.user = self.scope.get('user')
        
        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)  # Unauthorized
            return
        
        # Create room group name for user
        self.room_group_name = f'dashboard_{self.user.id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        # Accept connection
        await self.accept()
        
        # Initialize aggregator
        self.aggregator = await database_sync_to_async(RealTimeDashboardAggregator)(self.user)
        
        # Send initial connection message
        await self.send(text_data=json.dumps({
            'type': 'connection.established',
            'message': 'Dashboard WebSocket connected',
            'user_id': str(self.user.id),
            'timestamp': datetime.now().isoformat()
        }, cls=DjangoJSONEncoder))
        
        # Start periodic updates
        self.update_task = asyncio.create_task(self.send_periodic_updates())
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Cancel update task
        if self.update_task:
            self.update_task.cancel()
        
        # Leave room group
        if self.room_group_name:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """Handle messages from WebSocket client."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'configure':
                await self.handle_configuration(data)
            elif message_type == 'request_update':
                await self.send_dashboard_update()
            elif message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': datetime.now().isoformat()
                }, cls=DjangoJSONEncoder))
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': f'Unknown message type: {message_type}'
                }, cls=DjangoJSONEncoder))
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }, cls=DjangoJSONEncoder))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Error processing message: {str(e)}'
            }, cls=DjangoJSONEncoder))
    
    async def handle_configuration(self, data):
        """Handle client configuration updates."""
        config = data.get('config', {})
        
        # Update interval (minimum 10 seconds, maximum 300 seconds)
        new_interval = config.get('update_interval', self.update_interval)
        self.update_interval = max(10, min(300, new_interval))
        
        # Send confirmation
        await self.send(text_data=json.dumps({
            'type': 'configuration.updated',
            'config': {
                'update_interval': self.update_interval
            },
            'timestamp': datetime.now().isoformat()
        }, cls=DjangoJSONEncoder))
        
        # Restart update task with new interval
        if self.update_task:
            self.update_task.cancel()
        self.update_task = asyncio.create_task(self.send_periodic_updates())
    
    async def send_periodic_updates(self):
        """Send periodic dashboard updates."""
        try:
            while True:
                await self.send_dashboard_update()
                await asyncio.sleep(self.update_interval)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Update task error: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }, cls=DjangoJSONEncoder))
    
    async def send_dashboard_update(self):
        """Send dashboard update to client."""
        try:
            # Get live dashboard update
            dashboard_update = await database_sync_to_async(
                self.aggregator.get_live_dashboard_update
            )()
            
            # Convert to WebSocket message format
            message_data = {
                'type': 'dashboard.update',
                'data': {
                    'user_id': dashboard_update.user_id,
                    'timestamp': dashboard_update.timestamp.isoformat(),
                    'performance_score': dashboard_update.performance_score,
                    'metrics': [
                        {
                            'name': metric.name,
                            'value': float(metric.value),
                            'change': float(metric.change),
                            'trend': metric.trend,
                            'timestamp': metric.timestamp.isoformat(),
                            'confidence': metric.confidence
                        }
                        for metric in dashboard_update.metrics
                    ],
                    'alerts': dashboard_update.alerts
                },
                'metadata': {
                    'update_interval': self.update_interval,
                    'next_update': (datetime.now().timestamp() + self.update_interval) * 1000  # milliseconds
                }
            }
            
            await self.send(text_data=json.dumps(message_data, cls=DjangoJSONEncoder))
            
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Failed to get dashboard update: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }, cls=DjangoJSONEncoder))
    
    # Group message handlers
    async def dashboard_broadcast(self, event):
        """Handle broadcast messages to dashboard group."""
        await self.send(text_data=json.dumps(event['data'], cls=DjangoJSONEncoder))
    
    async def force_update(self, event):
        """Handle forced update requests."""
        await self.send_dashboard_update()


class DashboardNotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for dashboard notifications and alerts.
    Provides real-time alert streaming and notification management.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.room_group_name = None
    
    async def connect(self):
        """Handle WebSocket connection for notifications."""
        self.user = self.scope.get('user')
        
        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return
        
        # Create notifications room group
        self.room_group_name = f'dashboard_notifications_{self.user.id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'notifications.connected',
            'message': 'Dashboard notifications WebSocket connected',
            'user_id': str(self.user.id),
            'timestamp': datetime.now().isoformat()
        }, cls=DjangoJSONEncoder))
    
    async def disconnect(self, close_code):
        """Handle notification WebSocket disconnection."""
        if self.room_group_name:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """Handle notification acknowledgments and commands."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'acknowledge':
                # Handle alert acknowledgment
                alert_id = data.get('alert_id')
                await self.handle_alert_acknowledgment(alert_id)
            elif message_type == 'subscribe':
                # Handle notification subscription changes
                subscription = data.get('subscription', {})
                await self.handle_subscription_update(subscription)
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }, cls=DjangoJSONEncoder))
    
    async def handle_alert_acknowledgment(self, alert_id):
        """Handle alert acknowledgment from client."""
        # In a real implementation, you'd update the alert status in the database
        await self.send(text_data=json.dumps({
            'type': 'alert.acknowledged',
            'alert_id': alert_id,
            'timestamp': datetime.now().isoformat()
        }, cls=DjangoJSONEncoder))
    
    async def handle_subscription_update(self, subscription):
        """Handle notification subscription updates."""
        # Store subscription preferences (in real implementation, save to database)
        await self.send(text_data=json.dumps({
            'type': 'subscription.updated',
            'subscription': subscription,
            'timestamp': datetime.now().isoformat()
        }, cls=DjangoJSONEncoder))
    
    # Group message handlers
    async def send_alert(self, event):
        """Send alert notification to client."""
        await self.send(text_data=json.dumps({
            'type': 'alert.new',
            'alert': event['alert'],
            'timestamp': datetime.now().isoformat()
        }, cls=DjangoJSONEncoder))
    
    async def send_notification(self, event):
        """Send general notification to client."""
        await self.send(text_data=json.dumps({
            'type': 'notification.new',
            'notification': event['notification'],
            'timestamp': datetime.now().isoformat()
        }, cls=DjangoJSONEncoder))


# WebSocket routing configuration (for reference)
"""
# In routing.py:
from django.urls import re_path
from . import websocket_consumer

websocket_urlpatterns = [
    re_path(r'ws/dashboard/(?P<user_id>\w+)/$', websocket_consumer.DashboardConsumer.as_asgi()),
    re_path(r'ws/dashboard/notifications/(?P<user_id>\w+)/$', websocket_consumer.DashboardNotificationConsumer.as_asgi()),
]
"""