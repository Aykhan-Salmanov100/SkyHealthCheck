from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserLoginForm, UserRegistrationForm, UserProfileForm, UserPasswordChangeForm
from teams.models import Team
from health_checks.models import HealthCheckSession
from django.utils import timezone


def user_login(request):
    """Handle user login"""
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                next_url = request.GET.get('next', 'dashboard')
                return redirect(next_url)
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = UserLoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})


def register(request):
    """Handle user registration"""
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Registration successful! You can now log in.')
            return redirect('login')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def dashboard(request):
    """User dashboard showing teams and health checks"""
    user = request.user
    
    # For admins and senior managers, show all teams
    if user.is_admin() or user.is_senior_manager():
        teams = Team.objects.all()
    # For department leaders, show teams in their department
    elif user.is_department_leader() and user.department:
        teams = Team.objects.filter(department=user.department)
    # Otherwise, show teams the user belongs to
    else:
        teams = user.teams.all()
    
    # Get active health check sessions (either for all teams or just user's teams)
    now = timezone.now()
    active_sessions_query = HealthCheckSession.objects.filter(
        start_date__lte=now,
        end_date__gte=now
    )
    
    if not (user.is_admin() or user.is_senior_manager()):
        active_sessions_query = active_sessions_query.filter(team__in=teams)
    
    active_sessions = active_sessions_query.distinct()
    
    # Get recent sessions (for all accessible teams)
    recent_sessions_query = HealthCheckSession.objects.all()
    
    if not (user.is_admin() or user.is_senior_manager()):
        recent_sessions_query = recent_sessions_query.filter(team__in=teams)
    
    recent_sessions = recent_sessions_query.order_by('-start_date')[:5]
    
    # Get teams led by user
    teams_led = Team.objects.filter(team_memberships__user=user, team_memberships__is_leader=True)
    
    context = {
        'teams': teams,
        'active_sessions': active_sessions,
        'recent_sessions': recent_sessions,
        'teams_led': teams_led,
        'now': now
    }
    
    return render(request, 'accounts/dashboard.html', context)


@login_required
def profile(request):
    """Display user profile"""
    return render(request, 'accounts/profile.html', {'user': request.user})


@login_required
def edit_profile(request):
    """Edit user profile"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=request.user, user=request.user)
    
    return render(request, 'accounts/edit_profile.html', {'form': form})


@login_required
def change_password(request):
    """Change user password"""
    if request.method == 'POST':
        form = UserPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password has been updated successfully.')
            return redirect('profile')
    else:
        form = UserPasswordChangeForm(request.user)
    
    return render(request, 'accounts/change_password.html', {'form': form})
