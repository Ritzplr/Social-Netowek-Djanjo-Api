
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import UserProfile, FriendRequest
from .serializers import UserSerializer, FriendRequestSerializer
from rest_framework import generics
from django.core.cache import cache
from datetime import timedelta
from django.utils import timezone

class SignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').lower()
        password = request.data.get('password', '')

        if User.objects.filter(email=email).exists():
            return Response({'error': 'User with this email already exists'}, status=400)

        user = User.objects.create_user(username=email, email=email, password=password)
        return Response({'message': 'User created successfully'}, status=201)

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').lower()
        password = request.data.get('password', '')

        user = authenticate(request, username=email, password=password)
        if not user:
            return Response({'error': 'Invalid credentials'}, status=400)

        refresh = RefreshToken.for_user(user)
        return Response({'refresh': str(refresh), 'access': str(refresh.access_token)})

class UserSearchView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        keyword = self.request.query_params.get('q', '')
        if '@' in keyword:
            return User.objects.filter(email__iexact=keyword)
        return User.objects.filter(username__icontains=keyword)

class FriendRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        sender = request.user
        receiver_email = request.data.get('email')
        if not receiver_email:
            return Response({'error': 'Receiver email is required'}, status=400)

        try:
            receiver = User.objects.get(email=receiver_email)
        except User.DoesNotExist:
            return Response({'error': 'User does not exist'}, status=404)

        # Check if the request already exists
        if FriendRequest.objects.filter(sender=sender, receiver=receiver).exists():
            return Response({'error': 'Friend request already sent'}, status=400)

        # Rate limiting: Allow max 3 friend requests per minute
        cache_key = f'friend_requests_{sender.id}'
        friend_request_count = cache.get(cache_key, 0)
        if friend_request_count >= 3:
            return Response({'error': 'Too many friend requests sent, please wait.'}, status=429)

        # Create friend request
        friend_request = FriendRequest(sender=sender, receiver=receiver)
        friend_request.save()

        # Update rate limit cache
        cache.set(cache_key, friend_request_count + 1, timeout=60)  # 60 seconds timeout

        return Response({'message': 'Friend request sent successfully'}, status=201)

    def get(self, request):
        user = request.user

        # List all friends
        friends = user.userprofile.friends.all()
        friends_data = UserSerializer(friends, many=True).data

        # List pending friend requests
        pending_requests = FriendRequest.objects.filter(receiver=user, accepted=False, rejected=False)
        pending_requests_data = FriendRequestSerializer(pending_requests, many=True).data

        return Response({
            'friends': friends_data,
            'pending_requests': pending_requests_data
        }, status=200)
