from django.urls import path
from .views import *
from django.contrib.auth.views import LogoutView


urlpatterns = [
    path("signup/", create_user ,name="signup"),
    path("login/", login_view ,name="login"),
    path('logout/', logout_view,  name='logout'),
    path('contact/', contact_us, name='contact_us'),

]

