from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.user_profile, name='profile'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('financial-dashboard/', views.financial_dashboard, name='financial_dashboard'),
    
    # User management
    path('list/', views.UserListView.as_view(), name='user_list'),
    path('<int:pk>/', views.UserDetailView.as_view(), name='user_detail'),
    path('create/', views.UserCreateView.as_view(), name='user_create'),
    path('<int:pk>/update/', views.UserUpdateView.as_view(), name='user_update'),
    path('change-password/', views.change_password, name='change_password'),
    
    # Role management
    path('roles/', views.manage_user_roles, name='manage_roles'),
    path('assign-group/', views.assign_user_group, name='assign_user_group'),
] 