from django.urls import path

from apps.users.api.views import CurrentUserView, LoginView, LogoutView, RegisterView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="users-register"),
    path("login/", LoginView.as_view(), name="users-login"),
    path("logout/", LogoutView.as_view(), name="users-logout"),
    path("me/", CurrentUserView.as_view(), name="users-me"),
]
