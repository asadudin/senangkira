"""
Base utility serializers for SenangKira API.
"""

from rest_framework import serializers


class BaseModelSerializer(serializers.ModelSerializer):
    """
    Base serializer with common functionality.
    """
    
    def create(self, validated_data):
        """
        Create and return a new instance, setting the owner.
        """
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['owner'] = request.user
        return super().create(validated_data)


class TimestampedSerializer(serializers.ModelSerializer):
    """
    Serializer mixin for models with created_at/updated_at timestamps.
    """
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)