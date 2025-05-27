from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views
app_name="accounts"

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('signin/', views.signin, name='signin'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('password-reset/', views.request_password_reset, name='password_reset'),
    path('password-reset/confirm/', views.reset_password_confirm, name='password_reset_confirm'),
    path('update-user-data/', views.UpdateUserData.as_view(), name='update-user-data'),
    path('get-user-data/', views.GetUserData.as_view(), name='get-user-data'),
    path('profile/', views.UserProfileView.as_view(), name='user-profile'),
    path('change-password/', views.change_password, name='change_password'),
    # Addresses
    path('addresses/', views.UserAddressListCreateView.as_view(), name='user-address-list-create'),
    path('addresses/<int:pk>/', views.UserAddressRetrieveUpdateDestroyView.as_view(), name='user-address-detail'),
    #-----------------Admin--------------------------#
    path('create-admin-user/', views.create_admin_user, name='create-admin-user'),
    path('users/', views.UserListView.as_view(), name='user-list-create'),
    path('users/<int:pk>/', views.UserRetrieveUpdateDestroyView.as_view(), name='user-retrieve-update-destroy'),
    # User profile image 
    path('profile-images/', views.UserProfileImageListCreateView.as_view(), name='profile-image-list'),
    path('profile-images/<int:pk>/', views.UserProfileImageRetrieveUpdateDestroyView.as_view(), name='profile-image-detail'),

]
