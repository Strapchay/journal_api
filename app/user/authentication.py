from django.utils import timezone
from datetime import datetime, timedelta
from rest_framework import authentication, exceptions
from rest_framework.authtoken.models import Token

class ExpiringTokenAuthentication(authentication.TokenAuthentication):
    def authenticate_credentials(self,key):
        try:
            token = self.get_model().objects.get(key=key)
        except self.get_model().DoesNotExist:
            raise exceptions.AuthenticationFailed("Invalid Or Expired Token Provided")
        
        if not token.user.is_active:
            raise exceptions.AuthenticationFailed("Inactive User")
        
        current_time = timezone.now()

        if token.created < current_time - timedelta(hours=72):
            raise exceptions.AuthenticationFailed("Token has Expired")
        return token.user, token