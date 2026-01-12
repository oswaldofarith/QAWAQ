"""Custom decorators for authentication and permissions."""
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps


def admin_required(function=None):
    """
    Decorator for views that checks that the user is logged in and is an admin.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            
            # Check if user has profile and is admin
            if not hasattr(request.user, 'profile'):
                messages.error(request, 'Tu cuenta no tiene un perfil configurado. Contacta al administrador.')
                return redirect('dashboard')
            
            if request.user.profile.role != 'admin':
                messages.error(request, 'No tienes permisos para acceder a esta página.')
                return redirect('dashboard')
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    
    if function:
        return decorator(function)
    return decorator


def login_required_method(view_class):
    """
    Class decorator to apply login_required to all methods of a class-based view.
    """
    return method_decorator(login_required, name='dispatch')(view_class)


def admin_required_method(view_class):
    """
    Class decorator to apply admin_required to all methods of a class-based view.
    """
    original_dispatch = view_class.dispatch
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        if not hasattr(request.user, 'profile'):
            messages.error(request, 'Tu cuenta no tiene un perfil configurado.')
            return redirect('dashboard')
        
        if request.user.profile.role != 'admin':
            messages.error(request, 'No tienes permisos para acceder a esta función.')
            return redirect('dashboard')
        
        return original_dispatch(self, request, *args, **kwargs)
    
    view_class.dispatch = dispatch
    return view_class
