from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('health-check/', views.health_check, name='health-check'),
    path('ledger/', views.unified_ledger, name='unified_ledger'),
    path('dues/', views.due_report, name='due_report'),
    path('dues/export/<str:format>/', views.export_dues, name='export_dues'),
    path('book/', views.cash_bank_book, name='cash_bank_book'),
    path('book/export/<str:format>/', views.export_cash_bank_book, name='export_cash_bank_book'),
    path('bills/', views.bill_report, name='bill_report'),
    path('bills/export/<str:format>/', views.export_bill_report, name='export_bill_report'),
    
    # Role management
    path('api/run-setup-roles/', views.run_setup_roles, name='run_setup_roles'),
] 