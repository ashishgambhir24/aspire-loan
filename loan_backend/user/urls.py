from django.urls import path
from user import views


urlpatterns = [
    path('signin/', views.SignInView.as_view(), name='signin_view'),
    path('login/', views.LogInView.as_view(), name='login_view'),
]