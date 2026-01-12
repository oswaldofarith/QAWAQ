
# User Management Views

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
                Q(email__iconttains=search_query)
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


class UsuarioDetailView(DetailView):
    """View to display user profile details."""
    model = User
    template_name = 'monitor/usuario_detail.html'
    context_object_name = 'usuario'
    
    def get_queryset(self):
        return User.objects.select_related('profile')


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


class UsuarioUpdateView(View):
    """View to update user and profile."""
    
    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        profile = user.profile
        form = UserProfileForm(instance=profile)
        return render(request, 'monitor/usuario_form.html', {
            'form': form,
            'usuario': user,
            'title': 'Editar Usuario',
            'is_create': False
        })
    
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        profile = user.profile
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
