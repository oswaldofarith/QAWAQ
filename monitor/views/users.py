from django.views.generic import ListView, DetailView
from django.views import View
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.models import User

from ..models import UserProfile
from ..forms import UserProfileForm, PasswordChangeForm, MyProfileForm
from ..decorators import admin_required_method, login_required_method

@admin_required_method
class UsuarioListView(ListView):
    """View to list all users with their profiles."""
    model = User
    template_name = 'monitor/usuario_list.html'
    context_object_name = 'usuarios'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = User.objects.select_related('profile').filter(is_active=True)
        
        # Search functionality
        search_query = self.request.GET.get('q', '')
        if search_query:
            queryset = queryset.filter(
                Q(username__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query)
            )
        
        # Filter by role
        role_filter = self.request.GET.get('role', '')
        if role_filter:
            queryset = queryset.filter(profile__role=role_filter)
        
        return queryset.order_by('username')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        context['role_filter'] = self.request.GET.get('role', '')
        return context


@admin_required_method
class UsuarioDetailView(DetailView):
    """View to display user profile details."""
    model = User
    template_name = 'monitor/usuario_detail.html'
    context_object_name = 'usuario'
    
    def get_queryset(self):
        return User.objects.select_related('profile')
    
    def get_object(self, queryset=None):
        user = super().get_object(queryset)
        # Ensure profile exists for legacy users
        if not hasattr(user, 'profile'):
            UserProfile.objects.create(user=user)
        return user


@admin_required_method
class UsuarioCreateView(View):
    """View to create a new user with profile."""
    
    def get(self, request):
        form = UserProfileForm()
        return render(request, 'monitor/usuario_form.html', {
            'form': form,
            'title': 'Crear Usuario',
            'is_create': True
        })
    
    def post(self, request):
        form = UserProfileForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('usuario_list')
        return render(request, 'monitor/usuario_form.html', {
            'form': form,
            'title': 'Crear Usuario',
            'is_create': True
        })


@admin_required_method
class UsuarioUpdateView(View):
    """View to update user and profile."""
    
    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        # Create profile if it doesn't exist (for legacy users)
        profile, created = UserProfile.objects.get_or_create(user=user)
        form = UserProfileForm(instance=profile)
        return render(request, 'monitor/usuario_form.html', {
            'form': form,
            'usuario': user,
            'title': 'Editar Usuario',
            'is_create': False
        })
    
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        # Create profile if it doesn't exist (for legacy users)
        profile, created = UserProfile.objects.get_or_create(user=user)
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('usuario_detail', pk=pk)
        return render(request, 'monitor/usuario_form.html', {
            'form': form,
            'usuario': user,
            'title': 'Editar Usuario',
            'is_create': False
        })

class LoginView(View):
    """View to handle user login."""
    
    def get(self, request):
        # Redirect if already logged in
        if request.user.is_authenticated:
            return redirect('dashboard')
        
        return render(request, 'monitor/login.html', {
            'next': request.GET.get('next', '')
        })
    
    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember = request.POST.get('remember')
        next_url = request.POST.get('next', '/')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            
            # Handle "remember me"
            if not remember:
                request.session.set_expiry(0)  # Session expires on browser close
            else:
                request.session.set_expiry(1209600)  # 2 weeks
            
            messages.success(request, f'Bienvenido, {user.first_name or user.username}!')
            
            # Redirect to next or dashboard
            if next_url and next_url != '/login/':
                return redirect(next_url)
            return redirect('dashboard')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')
            return render(request, 'monitor/login.html', {
                'form': {'errors': True},
                'next': next_url
            })


class LogoutView(View):
    """View to handle user logout."""
    
    def get(self, request):
        # Clear all existing messages before logout
        storage = messages.get_messages(request)
        storage.used = True
        
        logout(request)
        messages.info(request, 'Ha cerrado sesión exitosamente.')
        return redirect('login')
    
    def post(self, request):
        # Clear all existing messages before logout
        storage = messages.get_messages(request)
        storage.used = True
        
        logout(request)
        messages.info(request, 'Ha cerrado sesión exitosamente.')
        return redirect('login')


@login_required_method
class ChangePasswordView(View):
    """Allow authenticated users to change their password."""
    
    def get(self, request):
        form = PasswordChangeForm(user=request.user)
        return render(request, 'monitor/change_password.html', {
            'form': form
        })
    
    def post(self, request):
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            # Update session hash to prevent logout
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Tu contraseña ha sido actualizada exitosamente.')
            return redirect('dashboard')
        return render(request, 'monitor/change_password.html', {
            'form': form
        })


@login_required_method
class MyProfileView(View):
    """Allow users to view and edit their own profile."""
    
    def get(self, request):
        profile = request.user.profile
        form = MyProfileForm(instance=profile, user=request.user)
        return render(request, 'monitor/my_profile.html', {
            'form': form,
            'profile': profile
        })
    
    def post(self, request):
        profile = request.user.profile
        form = MyProfileForm(
            request.POST,
            request.FILES,
            instance=profile,
            user=request.user
        )
        if form.is_valid():
            form.save()
            messages.success(request, 'Tu perfil ha sido actualizado exitosamente.')
            return redirect('my_profile')
        return render(request, 'monitor/my_profile.html', {
            'form': form,
            'profile': profile
        })
