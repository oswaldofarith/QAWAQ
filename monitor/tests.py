from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Equipo, Marca, TipoEquipo

class DashboardViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client.login(username='testuser', password='password')

    def test_dashboard_view_status_code(self):
        url = reverse('dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

class EquipoListViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client.login(username='testuser', password='password')
        
        # Create dummy data
        marca = Marca.objects.create(nombre='TestBrand')
        tipo = TipoEquipo.objects.create(nombre='TestType')
        Equipo.objects.create(id_equipo='TEST001', ip='192.168.1.1', marca=marca, tipo=tipo)

    def test_equipo_list_view_status_code(self):
        url = reverse('equipo_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_equipo_list_contains_data(self):
        url = reverse('equipo_list')
        response = self.client.get(url)
        self.assertContains(response, 'TEST001')

class ReporteViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client.login(username='testuser', password='password')

    def test_reporte_view_status_code(self):
        url = reverse('reportes')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
