from django.test import TestCase
from django.urls import reverse
from decimal import Decimal
from .models import Material, PurchaseOrder, PurchaseItem, InventoryEntry
from apps.suppliers.models import Supplier
from django.contrib.auth import get_user_model

User = get_user_model()

class PurchaseOrderInventoryUpdateTest(TestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        
        # Create a test supplier
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            phone='1234567890',
            address='123 Test St'
        )
        
        # Create a test material
        self.material = Material.objects.create(
            name='Test Material',
            unit='kg',
            current_stock=Decimal('0'),
            reorder_level=Decimal('10')
        )
        
    def test_purchase_order_auto_inventory_update(self):
        # Log in the test user
        self.client.login(username='testuser', password='testpassword')
        
        # Create a new purchase order with auto_update_inventory checked
        purchase_data = {
            'supplier': self.supplier.id,
            'purchase_date': '2023-05-01',
            'gst_percent': '5',
            'transport_cost': '100',
            'notes': 'Test purchase order',
            'auto_update_inventory': 'on',
            
            # Formset data for one purchase item
            'items-TOTAL_FORMS': '1',
            'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0',
            'items-MAX_NUM_FORMS': '1000',
            'items-0-material': self.material.id,
            'items-0-quantity': '50',
            'items-0-rate_per_unit': '10',
            'items-0-gst_applicable': 'on',
        }
        
        # Submit the form
        response = self.client.post(
            reverse('materials:purchase_order_create'),
            data=purchase_data,
            follow=True
        )
        
        # Check if the purchase order was created
        self.assertEqual(PurchaseOrder.objects.count(), 1)
        purchase_order = PurchaseOrder.objects.first()
        
        # Check if inventory was updated
        self.assertTrue(purchase_order.inventory_updated)
        
        # Check if the material stock was updated
        self.material.refresh_from_db()
        self.assertEqual(self.material.current_stock, Decimal('50'))
        
        # Check if an inventory entry was created
        self.assertEqual(InventoryEntry.objects.count(), 1)
        entry = InventoryEntry.objects.first()
        self.assertEqual(entry.material, self.material)
        self.assertEqual(entry.quantity, Decimal('50'))
        self.assertEqual(entry.entry_type, 'IN')
        self.assertEqual(entry.reference_type, 'PURCHASE')
        
    def test_purchase_order_without_auto_inventory_update(self):
        # Log in the test user
        self.client.login(username='testuser', password='testpassword')
        
        # Create a new purchase order with auto_update_inventory NOT checked
        purchase_data = {
            'supplier': self.supplier.id,
            'purchase_date': '2023-05-01',
            'gst_percent': '5',
            'transport_cost': '100',
            'notes': 'Test purchase order',
            # auto_update_inventory not included
            
            # Formset data for one purchase item
            'items-TOTAL_FORMS': '1',
            'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0',
            'items-MAX_NUM_FORMS': '1000',
            'items-0-material': self.material.id,
            'items-0-quantity': '50',
            'items-0-rate_per_unit': '10',
            'items-0-gst_applicable': 'on',
        }
        
        # Submit the form
        response = self.client.post(
            reverse('materials:purchase_order_create'),
            data=purchase_data,
            follow=True
        )
        
        # Check if the purchase order was created
        self.assertEqual(PurchaseOrder.objects.count(), 1)
        purchase_order = PurchaseOrder.objects.first()
        
        # Check that inventory was NOT updated
        self.assertFalse(purchase_order.inventory_updated)
        
        # Check that the material stock was NOT updated
        self.material.refresh_from_db()
        self.assertEqual(self.material.current_stock, Decimal('0'))
        
        # Check that no inventory entry was created
        self.assertEqual(InventoryEntry.objects.count(), 0)
