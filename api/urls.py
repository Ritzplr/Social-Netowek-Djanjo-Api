from django.urls import path
from .views import SignupView, LoginView, UserSearchView, FriendRequestView

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', LoginView.as_view(), name='login'),
    path('search/', UserSearchView.as_view(), name='user-search'),
    path('friends/', FriendRequestView.as_view(), name='friend-requests'),
]
