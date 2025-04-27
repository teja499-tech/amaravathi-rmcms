from django.urls import path
from . import views # Importing all views generically
from .views import (
    DeliveryListView, DeliveryCreateView, DeliveryDetailView, DeliveryUpdateView,
    ConcreteDeliveryCreateRedirectView,
)

app_name = 'customers'

urlpatterns = [
    # Customer URLs
    path('', views.CustomerListView.as_view(), name='customer_list'),
    path('create/', views.CustomerCreateView.as_view(), name='customer_create'),
    path('<int:pk>/', views.CustomerDetailView.as_view(), name='customer_detail'),
    path('<int:pk>/update/', views.CustomerUpdateView.as_view(), name='customer_update'),
    path('<int:pk>/delete/', views.CustomerDeleteView.as_view(), name='customer_delete'),
    path('<int:pk>/ledger/', views.CustomerLedgerView.as_view(), name='customer_ledger'),
    path('<int:pk>/ledger/excel/', views.CustomerLedgerExcelView.as_view(), name='customer_ledger_excel'),
    
    # Ledger URLs
    path('ledger/', views.CustomerLedgerListView.as_view(), name='ledger_list'),
    
    # Delivery URLs - Unified for both regular and concrete deliveries
    path('deliveries/', DeliveryListView.as_view(), name='delivery_list'),
    path('deliveries/create/', DeliveryCreateView.as_view(), name='delivery_create'),
    path('deliveries/<int:pk>/', DeliveryDetailView.as_view(), name='delivery_detail'),
    path('deliveries/<int:pk>/update/', DeliveryUpdateView.as_view(), name='delivery_update'),
    
    # Customer Payment URLs
    path('payments/', views.CustomerPaymentListView.as_view(), name='payment_list'),
    path('payments/create/', views.CustomerPaymentCreateView.as_view(), name='payment_create'),
    path('payments/<int:pk>/update/', views.CustomerPaymentUpdateView.as_view(), name='payment_update'),
    path('payments/<int:pk>/delete/', views.CustomerPaymentDeleteView.as_view(), name='payment_delete'),
    
    # Concrete Delivery URLs - Still need detail and list views
    path('concrete-deliveries/', views.ConcreteDeliveryListView.as_view(), name='concrete_delivery_list'),
    path('concrete-deliveries/create/', ConcreteDeliveryCreateRedirectView.as_view(), name='concrete_delivery_create'),  # Redirect to unified form
    path('concrete-deliveries/<int:pk>/', views.ConcreteDeliveryDetailView.as_view(), name='concrete_delivery_detail'),
    path('concrete-deliveries/<int:pk>/update/', views.ConcreteDeliveryUpdateView.as_view(), name='concrete_delivery_update'),
    
    # Mix Ratio URLs
    path('mixratios/', views.MixRatioListView.as_view(), name='mix_ratio_list'),
    path('mixratios/create/', views.MixRatioCreateView.as_view(), name='mix_ratio_create'),
    path('mixratios/<int:pk>/update/', views.MixRatioUpdateView.as_view(), name='mix_ratio_update'),
    path('mixratios/<int:pk>/delete/', views.MixRatioDeleteView.as_view(), name='mix_ratio_delete'),
    
    # Report URLs
    path('reports/delivery/', views.delivery_report, name='delivery_report'),
    
    # Risk Assessment URL
    path('risk-assessment/', views.CustomerRiskAssessmentView.as_view(), name='risk_assessment'),
    
    # API Endpoints
    path('api/deliveries/', views.customer_deliveries_api, name='api_customer_deliveries'),
    path('api/concrete-deliveries/', views.concrete_deliveries_api, name='api_concrete_deliveries'),
] 