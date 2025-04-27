from django.urls import path
from . import views
from .views import (
    MaterialListView, MaterialDetailView, MaterialCreateView, MaterialUpdateView, MaterialDeleteView,
    InventoryView, PurchaseOrderListView, PurchaseOrderDetailView, PurchaseOrderCreateView, 
    PurchaseOrderUpdateView, PurchaseOrderDeleteView, SmartSummaryDashboardView,
    PurchaseOrderDetailsAPIView
)

app_name = 'materials'

urlpatterns = [
    # Material URLs
    path('', MaterialListView.as_view(), name='material_list'),
    path('<int:pk>/', MaterialDetailView.as_view(), name='material_detail'),
    path('create/', MaterialCreateView.as_view(), name='material_create'),
    path('<int:pk>/update/', MaterialUpdateView.as_view(), name='material_update'),
    path('<int:pk>/delete/', MaterialDeleteView.as_view(), name='material_delete'),
    
    # Inventory URLs
    path('inventory/', InventoryView.as_view(), name='inventory_list'),
    path('inventory/update/', views.update_inventory, name='inventory_update'),
    
    # Purchase Order URLs
    path('purchase/', PurchaseOrderListView.as_view(), name='purchase_order_list'),
    path('purchase/<int:pk>/', PurchaseOrderDetailView.as_view(), name='purchase_order_detail'),
    path('purchase/create/', PurchaseOrderCreateView.as_view(), name='purchase_order_create'),
    path('purchase/<int:pk>/update/', PurchaseOrderUpdateView.as_view(), name='purchase_order_update'),
    path('purchase/<int:pk>/delete/', PurchaseOrderDeleteView.as_view(), name='purchase_order_delete'),
    
    # Dashboard URLs
    path('dashboard/', SmartSummaryDashboardView.as_view(), name='smart_summary'),
    
    # API URLs
    path('api/purchase-orders/<int:pk>/details/', PurchaseOrderDetailsAPIView.as_view(), name='purchase_order_details_api'),
] 