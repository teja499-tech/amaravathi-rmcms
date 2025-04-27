from django.urls import path
from . import views

app_name = 'employees'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Employee URLs
    path('', views.EmployeeListView.as_view(), name='employee_list'),
    path('<int:pk>/', views.EmployeeDetailView.as_view(), name='employee_detail'),
    path('create/', views.EmployeeCreateView.as_view(), name='employee_create'),
    path('<int:pk>/update/', views.EmployeeUpdateView.as_view(), name='employee_update'),
    path('<int:pk>/delete/', views.EmployeeDeleteView.as_view(), name='employee_delete'),
    
    # Salary Record URLs
    path('salaries/', views.SalaryRecordListView.as_view(), name='salary_record_list'),
    path('salaries/<int:pk>/', views.SalaryRecordDetailView.as_view(), name='salary_record_detail'),
    path('salaries/create/', views.SalaryRecordCreateView.as_view(), name='salary_record_create'),
    path('salaries/<int:pk>/update/', views.SalaryRecordUpdateView.as_view(), name='salary_record_update'),
    path('salaries/<int:pk>/delete/', views.SalaryRecordDeleteView.as_view(), name='salary_record_delete'),
    path('salaries/<int:pk>/mark-paid/', views.mark_as_paid, name='mark_as_paid'),
] 