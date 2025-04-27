from django.urls import path
from django.urls import reverse
from django.urls import reverse_lazy
from django.urls import NoReverseMatch
from django.views.generic import RedirectView
from . import views

app_name = 'expenses'

urlpatterns = [
    # Dashboard and Reports
    path('dashboard/', views.expense_dashboard, name='dashboard'),
    path('report/', views.expense_report, name='report'),

    # Expense Categories
    path('categories/', views.ExpenseCategoryListView.as_view(), name='category_list'),
    path('categories/add/', views.ExpenseCategoryCreateView.as_view(), name='category_create'),
    path('categories/<int:pk>/edit/', views.ExpenseCategoryUpdateView.as_view(), name='category_update'),
    
    # Vehicles
    path('vehicles/', views.VehicleListView.as_view(), name='vehicle_list'),
    path('vehicles/add/', views.VehicleCreateView.as_view(), name='vehicle_create'),
    path('vehicles/<int:pk>/', views.VehicleDetailView.as_view(), name='vehicle_detail'),
    path('vehicles/<int:pk>/edit/', views.VehicleUpdateView.as_view(), name='vehicle_update'),
    path('vehicles/<int:pk>/delete/', views.VehicleDeleteView.as_view(), name='vehicle_delete'),
    
    # Expenses
    path('', views.ExpenseListView.as_view(), name='expense_list'),
    path('add/', views.ExpenseCreateView.as_view(), name='expense_create'),
    path('<int:pk>/', views.ExpenseDetailView.as_view(), name='expense_detail'),
    path('<int:pk>/edit/', views.ExpenseUpdateView.as_view(), name='expense_update'),
    path('<int:pk>/delete/', views.ExpenseDeleteView.as_view(), name='expense_delete'),
    
    # Salaries - Redirects to Employees app
    path('salaries/', RedirectView.as_view(pattern_name='employees:salary_record_list', permanent=True), name='salary_list'),
    path('salaries/add/', RedirectView.as_view(pattern_name='employees:salary_record_create', permanent=True), name='salary_create'),
    path('salaries/<int:pk>/', views.salary_detail_redirect, name='salary_detail'),
    path('salaries/<int:pk>/edit/', views.salary_edit_redirect, name='salary_update'),
    path('salaries/<int:pk>/delete/', views.salary_delete_redirect, name='salary_delete'),
] 