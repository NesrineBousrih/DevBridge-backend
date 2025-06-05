from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import  ProjectViewSet, RecentActivityView, TechnologyDistributionView, UserRegistrationView, UserLoginView, UserViewSet,FrameworkViewSet, UsersOverviewView, WeeklyActivityView
from api import views



router = DefaultRouter()
router.register(r'users', UserViewSet,basename='users')
router.register(r'frameworks', FrameworkViewSet,basename='frameworks')
router.register(r'projects', ProjectViewSet,basename='projects')


urlpatterns = [
    path('', include(router.urls)),  # Routes CRUD
    path('register/', UserRegistrationView.as_view(), name='register'),  # Inscription utilisateur
    path('login/', UserLoginView.as_view(), name='login'),  # Connexion utilisateur
    path('weekly-activity/', WeeklyActivityView.as_view(), name='weekly-activity'),
    path('users-overview/', UsersOverviewView.as_view(), name='users-overview'),
    path('technology-distribution/', TechnologyDistributionView.as_view(), name='technology-distribution'),
    path('recent-activity/', RecentActivityView.as_view(), name='recent-activity'),
    

]
