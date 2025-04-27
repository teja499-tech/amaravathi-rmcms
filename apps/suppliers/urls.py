from django.urls import path, reverse_lazy
from django.views.generic.base import RedirectView
from . import views

app_name = 'suppliers'

urlpatterns = [
    path('', views.SupplierListView.as_view(), name='supplier_list'),
    path('create/', views.SupplierCreateView.as_view(), name='supplier_create'),
    path('<int:pk>/', views.SupplierDetailView.as_view(), name='supplier_detail'),
    path('<int:pk>/update/', views.SupplierUpdateView.as_view(), name='supplier_update'),
    path('<int:pk>/delete/', views.SupplierDeleteView.as_view(), name='supplier_delete'),
    path('<int:pk>/ledger/', views.SupplierLedgerView.as_view(), name='supplier_ledger'),
    
    # Redirect purchase URLs to materials app
    path('purchases/', RedirectView.as_view(url=reverse_lazy('materials:purchase_order_list')), name='purchase_list'),
    path('purchases/create/', RedirectView.as_view(url=reverse_lazy('materials:purchase_order_create')), name='purchase_create'),
    
    # Legacy URLs that will be redirected but maintain backwards compatibility
    path('purchases/<int:pk>/', views.PurchaseRedirectView.as_view(), name='purchase_detail'),
    path('purchases/<int:pk>/update/', views.PurchaseUpdateRedirectView.as_view(), name='purchase_update'),
    path('purchases/<int:pk>/delete/', views.PurchaseDeleteRedirectView.as_view(), name='purchase_delete'),
    
    path('payments/', views.SupplierPaymentListView.as_view(), name='payment_list'),
    path('payments/create/', views.SupplierPaymentCreateView.as_view(), name='payment_create'),
    path('payments/create/supplier/<int:supplier_id>/', views.SupplierPaymentCreateView.as_view(), name='payment_create_for_supplier'),
    path('payments/create/purchase/<int:purchase_id>/', views.SupplierPaymentCreateView.as_view(), name='payment_create_from_purchase'),
    path('payments/<int:pk>/update/', views.SupplierPaymentUpdateView.as_view(), name='payment_update'),
    path('payments/<int:pk>/delete/', views.SupplierPaymentDeleteView.as_view(), name='payment_delete'),
    
    path('payments/priority/', views.SupplierPaymentPriorityView.as_view(), name='payment_priority'),
    
    path('test-upload/', views.test_file_upload, name='test_upload'),
    
    # API endpoints
    path('api/<int:supplier_id>/purchase-orders/', views.SupplierPurchaseOrdersAPIView.as_view(), name='api_supplier_purchase_orders'),
] 