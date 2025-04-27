from django.urls import path
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from . import views

app_name = 'accounts'

urlpatterns = [
    # Redirect /accounts/login/ to the main login URL
    path('login/', lambda request: redirect('/login/?next=' + request.GET.get('next', '/'), permanent=True)),
    
    # Reports and Settings
    path('reports/profit-loss/', views.profit_loss_report, name='profit_loss_report'),
    path('settings/', views.settings_view, name='settings'),
    
    # Ledger and Books
    path('ledger/', views.unified_ledger_view, name='unified_ledger'),
    path('books/cash/', views.cash_book_view, name='cash_book'),
    path('books/bank/', views.bank_book_view, name='bank_book'),
    
    # Bank Accounts
    path('bank-accounts/', views.bank_account_list, name='bank_account_list'),
    path('bank-accounts/create/', views.bank_account_create, name='bank_account_create'),
    path('bank-accounts/<int:pk>/update/', views.bank_account_update, name='bank_account_update'),
    path('bank-accounts/<int:pk>/delete/', views.bank_account_delete, name='bank_account_delete'),
    
    # Bank Transactions
    path('transactions/create/', views.transaction_create, name='transaction_create'),
    path('transactions/<int:pk>/update/', views.transaction_update, name='transaction_update'),
    path('transactions/<int:pk>/delete/', views.transaction_delete, name='transaction_delete'),
    
    # Cash Transactions
    path('cash/create/', views.cash_transaction_create, name='cash_transaction_create'),
    path('cash/<int:pk>/update/', views.cash_transaction_update, name='cash_transaction_update'),
    path('cash/<int:pk>/delete/', views.cash_transaction_delete, name='cash_transaction_delete'),
] 