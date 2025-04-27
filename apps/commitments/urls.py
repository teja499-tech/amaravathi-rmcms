from django.urls import path
from . import views

app_name = 'commitments'

urlpatterns = [
    # Category URLs
    path('categories/', views.CommitmentCategoryListView.as_view(), name='category_list'),
    path('categories/add/', views.CommitmentCategoryCreateView.as_view(), name='category_create'),
    path('categories/<int:pk>/edit/', views.CommitmentCategoryUpdateView.as_view(), name='category_update'),
    path('categories/<int:pk>/delete/', views.CommitmentCategoryDeleteView.as_view(), name='category_delete'),
    
    # Commitment URLs
    path('', views.CommitmentListView.as_view(), name='commitment_list'),
    path('<int:pk>/', views.CommitmentDetailView.as_view(), name='commitment_detail'),
    path('add/', views.CommitmentCreateView.as_view(), name='commitment_create'),
    path('<int:pk>/edit/', views.CommitmentUpdateView.as_view(), name='commitment_update'),
    path('<int:pk>/delete/', views.CommitmentDeleteView.as_view(), name='commitment_delete'),
    
    # Payment URLs
    path('payments/add/', views.PaymentCreateView.as_view(), name='payment_create'),
    path('payments/add/<int:commitment_id>/', views.PaymentCreateView.as_view(), name='payment_create_for_commitment'),
    path('payments/<int:pk>/', views.PaymentDetailView.as_view(), name='payment_detail'),
    path('payments/<int:pk>/edit/', views.PaymentUpdateView.as_view(), name='payment_update'),
    path('payments/<int:pk>/delete/', views.PaymentDeleteView.as_view(), name='payment_delete'),
] 