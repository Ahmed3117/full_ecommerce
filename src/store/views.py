from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import StoreRequest, Store, StoreReporting
from .serializers import StoreRequestSerializer, StoreSerializer, StoreReportingSerializer
from django.shortcuts import get_object_or_404



class StoreRequestListCreateView(generics.ListCreateAPIView):
    serializer_class = StoreRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return StoreRequest.objects.all().order_by('-date_added')
        return StoreRequest.objects.filter(user=self.request.user).order_by('-date_added')

    def create(self, request, *args, **kwargs):
        # Check if user already has a store request
        existing_request = StoreRequest.objects.filter(user=request.user).first()
        
        if existing_request:
            serializer = self.get_serializer(existing_request)
            return Response(
                {
                    'message': 'You already have a pending store request',
                    'your_request': serializer.data
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Proceed with normal creation if no existing request
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class StoreRequestRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = StoreRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return StoreRequest.objects.all()
        return StoreRequest.objects.filter(user=self.request.user)

class ApproveStoreRequestView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk):
        store_request = get_object_or_404(StoreRequest, pk=pk)
        
        if store_request.status != 'pending':
            return Response(
                {'error': 'Request has already been processed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create the store
        store = Store.objects.create(
            user=store_request.user,
            name=f"{store_request.first_name} {store_request.last_name}",
            image=store_request.image,
            government=store_request.government,
            address=store_request.address,
            phone1=store_request.phone1,
            phone2=store_request.phone2,
            email=store_request.email,
            whatsapp_number=store_request.whatsapp_number,
            facebook_link=store_request.facebook_link,
            telegram_link=store_request.telegram_link,
            instagram_link=store_request.instagram_link,
            youtube_link=store_request.youtube_link,
            tiktok_link=store_request.tiktok_link,
        )
        
        # Update user type
        store_request.user.user_type = 'store'
        store_request.user.save()
        
        # Update request status
        store_request.status = 'accepted'
        store_request.save()
        
        return Response(
            {'message': 'Store request approved and store created successfully'},
            status=status.HTTP_200_OK
        )

class RejectStoreRequestView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk):
        store_request = get_object_or_404(StoreRequest, pk=pk)
        refuse_reason = request.data.get('refuse_reason', '')
        
        if store_request.status != 'pending':
            return Response(
                {'error': 'Request has already been processed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        store_request.status = 'refused'
        store_request.refuse_reason = refuse_reason
        store_request.save()
        
        return Response(
            {'message': 'Store request rejected successfully'},
            status=status.HTTP_200_OK
        )

class StoreListView(generics.ListAPIView):
    serializer_class = StoreSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    queryset = Store.objects.all()

class StoreRetrieveView(generics.RetrieveAPIView):
    serializer_class = StoreSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    queryset = Store.objects.all()

class StoreReportingListCreateView(generics.ListCreateAPIView):
    serializer_class = StoreReportingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return StoreReporting.objects.all().order_by('-date')
        return StoreReporting.objects.filter(user=self.request.user).order_by('-date')

    def perform_create(self, serializer):
        # Get store instance from the provided ID
        store_id = self.request.data.get('store')
        store = get_object_or_404(Store, id=store_id)
        
        serializer.save(
            user=self.request.user,
            store=store
        )

class StoreReportingRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = StoreReportingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return StoreReporting.objects.all()
        return StoreReporting.objects.filter(user=self.request.user)