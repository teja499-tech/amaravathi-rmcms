from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.http import HttpResponseRedirect

from .models import CommitmentCategory, OperationalCommitment, CommitmentPayment
from .forms import (
    CommitmentCategoryForm, OperationalCommitmentForm, 
    CommitmentPaymentForm, CommitmentFilterForm
)

# Category Views
class CommitmentCategoryListView(LoginRequiredMixin, ListView):
    model = CommitmentCategory
    template_name = 'commitments/category_list.html'
    context_object_name = 'categories'
    paginate_by = 10

class CommitmentCategoryCreateView(LoginRequiredMixin, CreateView):
    model = CommitmentCategory
    form_class = CommitmentCategoryForm
    template_name = 'commitments/category_form.html'
    success_url = reverse_lazy('commitments:category_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Category created successfully!')
        return super().form_valid(form)

class CommitmentCategoryUpdateView(LoginRequiredMixin, UpdateView):
    model = CommitmentCategory
    form_class = CommitmentCategoryForm
    template_name = 'commitments/category_form.html'
    success_url = reverse_lazy('commitments:category_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Category updated successfully!')
        return super().form_valid(form)

class CommitmentCategoryDeleteView(LoginRequiredMixin, DeleteView):
    model = CommitmentCategory
    template_name = 'commitments/category_confirm_delete.html'
    success_url = reverse_lazy('commitments:category_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Category deleted successfully!')
        return super().delete(request, *args, **kwargs)

# Operational Commitment Views
class CommitmentListView(LoginRequiredMixin, ListView):
    model = OperationalCommitment
    template_name = 'commitments/commitment_list.html'
    context_object_name = 'commitments'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = OperationalCommitment.objects.all()
        
        # Apply filters from the filter form
        form = CommitmentFilterForm(self.request.GET)
        
        if form.is_valid():
            category = form.cleaned_data.get('category')
            payment_frequency = form.cleaned_data.get('payment_frequency')
            status = form.cleaned_data.get('status')
            due_status = form.cleaned_data.get('due_status')
            search = form.cleaned_data.get('search')
            
            if category:
                queryset = queryset.filter(category=category)
                
            if payment_frequency:
                queryset = queryset.filter(payment_frequency=payment_frequency)
                
            if status:
                queryset = queryset.filter(status=status)
            
            today = timezone.now().date()
            
            if due_status == 'due_today':
                queryset = queryset.filter(next_payment_date=today)
            elif due_status == 'due_soon':
                queryset = queryset.filter(
                    next_payment_date__gt=today,
                    next_payment_date__lte=today + timezone.timedelta(days=7)
                )
            elif due_status == 'overdue':
                queryset = queryset.filter(next_payment_date__lt=today)
                
            if search:
                queryset = queryset.filter(
                    Q(title__icontains=search) |
                    Q(description__icontains=search) |
                    Q(payee_name__icontains=search) |
                    Q(reference_number__icontains=search)
                )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = CommitmentFilterForm(self.request.GET)
        
        # Add counts for different due statuses
        today = timezone.now().date()
        
        context['due_today_count'] = OperationalCommitment.objects.filter(
            next_payment_date=today, 
            status='active',
            is_active=True
        ).count()
        
        context['due_soon_count'] = OperationalCommitment.objects.filter(
            next_payment_date__gt=today,
            next_payment_date__lte=today + timezone.timedelta(days=7),
            status='active',
            is_active=True
        ).count()
        
        context['overdue_count'] = OperationalCommitment.objects.filter(
            next_payment_date__lt=today,
            status='active',
            is_active=True
        ).count()
        
        return context

class CommitmentDetailView(LoginRequiredMixin, DetailView):
    model = OperationalCommitment
    template_name = 'commitments/commitment_detail.html'
    context_object_name = 'commitment'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add payment history
        context['payments'] = self.object.payments.all().order_by('-payment_date')
        
        # Add payment form for adding new payments
        context['payment_form'] = CommitmentPaymentForm(initial={'commitment': self.object})
        
        return context

class CommitmentCreateView(LoginRequiredMixin, CreateView):
    model = OperationalCommitment
    form_class = OperationalCommitmentForm
    template_name = 'commitments/commitment_form.html'
    
    def get_success_url(self):
        return reverse_lazy('commitments:commitment_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Operational commitment created successfully!')
        return super().form_valid(form)

class CommitmentUpdateView(LoginRequiredMixin, UpdateView):
    model = OperationalCommitment
    form_class = OperationalCommitmentForm
    template_name = 'commitments/commitment_form.html'
    
    def get_success_url(self):
        return reverse_lazy('commitments:commitment_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Operational commitment updated successfully!')
        return super().form_valid(form)

class CommitmentDeleteView(LoginRequiredMixin, DeleteView):
    model = OperationalCommitment
    template_name = 'commitments/commitment_confirm_delete.html'
    success_url = reverse_lazy('commitments:commitment_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Operational commitment deleted successfully!')
        return super().delete(request, *args, **kwargs)

# Payment Views
class PaymentCreateView(LoginRequiredMixin, CreateView):
    model = CommitmentPayment
    form_class = CommitmentPaymentForm
    template_name = 'commitments/payment_form.html'
    
    def get_initial(self):
        initial = super().get_initial()
        commitment_id = self.kwargs.get('commitment_id')
        if commitment_id:
            initial['commitment'] = get_object_or_404(OperationalCommitment, pk=commitment_id)
            initial['payment_date'] = timezone.now().date()
        return initial
    
    def get_success_url(self):
        return reverse_lazy('commitments:commitment_detail', kwargs={'pk': self.object.commitment.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Payment recorded successfully!')
        response = super().form_valid(form)
        
        # Update commitment next payment date
        self.object.commitment.update_next_payment_date()
        
        return response

class PaymentUpdateView(LoginRequiredMixin, UpdateView):
    model = CommitmentPayment
    form_class = CommitmentPaymentForm
    template_name = 'commitments/payment_form.html'
    
    def get_success_url(self):
        return reverse_lazy('commitments:commitment_detail', kwargs={'pk': self.object.commitment.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Payment updated successfully!')
        return super().form_valid(form)

class PaymentDeleteView(LoginRequiredMixin, DeleteView):
    model = CommitmentPayment
    template_name = 'commitments/payment_confirm_delete.html'
    
    def get_success_url(self):
        return reverse_lazy('commitments:commitment_detail', kwargs={'pk': self.object.commitment.pk})
    
    def delete(self, request, *args, **kwargs):
        commitment = self.get_object().commitment
        messages.success(request, 'Payment deleted successfully!')
        response = super().delete(request, *args, **kwargs)
        
        # Update commitment next payment date
        commitment.update_next_payment_date()
        
        return response

class PaymentDetailView(LoginRequiredMixin, DetailView):
    model = CommitmentPayment
    template_name = 'commitments/payment_detail.html'
    context_object_name = 'payment'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['commitment'] = self.object.commitment
        return context
