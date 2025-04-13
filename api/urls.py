from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import  ProjectViewSet, UserRegistrationView, UserLoginView, UserViewSet,FrameworkViewSet



router = DefaultRouter()
router.register(r'users', UserViewSet,basename='users')
router.register(r'frameworks', FrameworkViewSet,basename='frameworks')
router.register(r'projects', ProjectViewSet,basename='projects')


urlpatterns = [
    path('', include(router.urls)),  # Routes CRUD
    path('register/', UserRegistrationView.as_view(), name='register'),  # Inscription utilisateur
    path('login/', UserLoginView.as_view(), name='login'),  # Connexion utilisateur

]
