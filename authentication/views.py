"""
Enhanced authentication views for SenangKira API.
Includes security features, logging, and comprehensive error handling.
"""

from rest_framework import generics, status, views
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model, authenticate
from django.utils import timezone  
from django.db import transaction
import logging
import ipaddress

from .serializers import (
    UserSerializer, 
    RegisterSerializer, 
    SenangKiraTokenObtainPairSerializer,
    ChangePasswordSerializer
)

logger = logging.getLogger(__name__)
User = get_user_model()


class SenangKiraTokenObtainPairView(TokenObtainPairView):
    """
    Enhanced JWT token obtain view with logging and security features.
    """
    serializer_class = SenangKiraTokenObtainPairSerializer
    
    def post(self, request, *args, **kwargs):
        """Enhanced token obtain with security logging."""
        ip_address = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            # Log successful login
            try:
                email = request.data.get('email', '')
                user = User.objects.get(email=email)
                user.last_login = timezone.now()
                user.save(update_fields=['last_login'])
                
                logger.info(f"Successful login: {email} from {ip_address}")
            except User.DoesNotExist:
                pass
        else:
            # Log failed login attempt
            email = request.data.get('email', 'unknown')
            logger.warning(f"Failed login attempt: {email} from {ip_address}")
        
        return response
    
    def get_client_ip(self, request):
        """Get client IP address safely."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        
        try:
            # Validate IP address
            ipaddress.ip_address(ip)
            return ip
        except ValueError:
            return 'unknown'


class RegisterView(generics.CreateAPIView):
    """
    Enhanced user registration endpoint with security features.
    POST /api/auth/register/
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        """Enhanced registration with logging and token generation."""
        ip_address = self.get_client_ip(request)
        
        with transaction.atomic():
            response = super().create(request, *args, **kwargs)
            
            if response.status_code == 201:
                user = User.objects.get(email=response.data['email'])
                
                # Generate tokens for immediate login after registration
                refresh = RefreshToken.for_user(user)
                
                # Update response with tokens
                response.data.update({
                    'tokens': {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                    },
                    'user': {
                        'id': str(user.id),
                        'email': user.email,
                        'username': user.username,
                        'company_name': user.company_name,
                    }
                })
                
                logger.info(f"New user registered: {user.email} from {ip_address}")
        
        return response
    
    def get_client_ip(self, request):
        """Get client IP address safely."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        
        try:
            ipaddress.ip_address(ip)
            return ip
        except ValueError:
            return 'unknown'


class ProfileView(generics.RetrieveUpdateAPIView):
    """
    Enhanced user profile management endpoint.
    GET/PUT /api/auth/profile/
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        """Enhanced profile update with logging."""
        response = super().update(request, *args, **kwargs)
        
        if response.status_code == 200:
            logger.info(f"Profile updated: {request.user.email}")
        
        return response


class ChangePasswordView(generics.UpdateAPIView):
    """
    Password change endpoint with security validation.
    PUT /api/auth/change-password/
    """
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        """Handle password change with security logging."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = self.get_object()
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        # Log password change
        ip_address = self.get_client_ip(request)
        logger.info(f"Password changed: {user.email} from {ip_address}")
        
        return Response({
            'message': 'Password updated successfully',
            'user': {
                'id': str(user.id),
                'email': user.email,
                'username': user.username,
            }
        })
    
    def get_client_ip(self, request):
        """Get client IP address safely."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0] 
        else:
            ip = request.META.get('REMOTE_ADDR')
        
        try:
            ipaddress.ip_address(ip)
            return ip
        except ValueError:
            return 'unknown'


class LogoutView(views.APIView):
    """
    Logout endpoint that blacklists refresh tokens.
    POST /api/auth/logout/
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Logout user and blacklist refresh token."""
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            # Log logout
            ip_address = self.get_client_ip(request)
            logger.info(f"User logout: {request.user.email} from {ip_address}")
            
            return Response({
                'message': 'Successfully logged out'
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Logout error for {request.user.email}: {str(e)}")
            return Response({
                'error': 'Invalid token'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def get_client_ip(self, request):
        """Get client IP address safely."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        
        try:
            ipaddress.ip_address(ip)
            return ip
        except ValueError:
            return 'unknown'


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_info(request):
    """
    Get current user information.
    GET /api/auth/me/
    """
    user = request.user
    return Response({
        'id': str(user.id),
        'email': user.email,
        'username': user.username,
        'company_name': user.company_name,
        'company_address': user.company_address,
        'date_joined': user.date_joined,
        'last_login': user.last_login,
        'is_active': user.is_active,
    })