from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

class SignInView(APIView):
    permission_classes=[AllowAny]
    def post(self, request):
        username = request.data['username']
        try:
            user = User.objects.get(username=username)
            return Response('user already exist')
        except User.DoesNotExist:
            if request.data.get('is_superuser', False):
                user = User.objects.create_superuser(username=username, password=request.data['password'])
            else:
                user = User.objects.create_user(username=username, password=request.data['password'])

        if request.data.get('is_staff', False):
            user.is_staff = True
            user.full_clean()
            user.save()

        token = RefreshToken.for_user(user)
        return Response(str(token.access_token))
    
class LogInView(APIView):
    permission_classes=[AllowAny]
    def post(self, request):
        user = authenticate(username=request.data['username'], password=request.data['password'])
        if user is None:
            return Response("Invalid username or password")
        else:
            token = RefreshToken.for_user(user)
            return Response(str(token.access_token))
