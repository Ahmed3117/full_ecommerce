
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
import rest_framework.filters as rest_filters
from about.models import FAQ, About, AboutDescription, Count
from about.serializers import AboutDescriptionSerializer, AboutSerializer, CountSerializer, FAQSerializer

# CRUD for About
class SingletonAboutAPIView(APIView):
    """
    GET: Retrieve the single About object with its descriptions.
    PUT/PATCH: Update the single About object.
    POST: Create it only if it doesn't exist (optional).
    """

    def get_object(self):
        return About.objects.first()

    def get(self, request):
        about = self.get_object()
        if not about:
            return Response({"detail": "About content not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = AboutSerializer(about, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        if About.objects.exists():
            return Response({"detail": "About already exists."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = AboutSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        about = self.get_object()
        if not about:
            return self.post(request)
        serializer = AboutSerializer(about, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        about = self.get_object()
        if not about:
            return Response({"detail": "About not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = AboutSerializer(about, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# CRUD for AboutDescription
class AboutDescriptionListCreateAPIView(generics.ListCreateAPIView):
    queryset = AboutDescription.objects.all()
    serializer_class = AboutDescriptionSerializer
    filter_backends = [DjangoFilterBackend, rest_filters.SearchFilter]
    filterset_fields = ['about', 'is_active']
    search_fields = ['description','title']


class AboutDescriptionRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = AboutDescription.objects.all()
    serializer_class = AboutDescriptionSerializer

# CRUD for FAQ
class FAQListAPIView(generics.ListAPIView):
    queryset = FAQ.objects.all()
    serializer_class = FAQSerializer
    filter_backends = [DjangoFilterBackend, rest_filters.SearchFilter]
    filterset_fields = ['is_active']
    search_fields = ['title', 'description']

#^ < ==========================Dashboard endpoints========================== >

class FAQListCreateAPIView(generics.ListCreateAPIView):
    queryset = FAQ.objects.all()
    serializer_class = FAQSerializer
    filter_backends = [DjangoFilterBackend, rest_filters.SearchFilter]
    filterset_fields = ['is_active']
    search_fields = ['title', 'description']

class FAQRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = FAQ.objects.all()
    serializer_class = FAQSerializer
    

class CountView(generics.RetrieveUpdateAPIView):
    serializer_class = CountSerializer

    def get_object(self):
        obj, _ = Count.objects.get_or_create()
        return obj




