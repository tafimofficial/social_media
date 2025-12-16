from django.urls import path, re_path
from django.views.static import serve
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/edit/', views.edit_profile_view, name='edit_profile'),
    path('profile/update/cover/', views.update_cover_view, name='update_cover'),
    path('profile/update/avatar/', views.update_avatar_view, name='update_avatar'),
    path('profile/update/bio/', views.update_bio_view, name='update_bio'),
    path('post/like/<int:post_id>/', views.like_post_view, name='like_post'),
    path('post/comment/add/', views.add_comment_ajax, name='add_comment_ajax'),
    path('post/edit/<int:post_id>/', views.edit_post_view, name='edit_post'),
    path('post/delete/<int:post_id>/', views.delete_post_view, name='delete_post'),
    path('post/share/<int:post_id>/', views.share_post_view, name='share_post'),
    path('post/create/', views.create_post_view, name='create_post'),
    
    # Friend System
    path('friends/', views.friends_view, name='friends'),
    path('friend/add/<str:username>/', views.send_friend_request, name='send_friend_request'),
    path('friend/accept/<int:request_id>/', views.accept_friend_request, name='accept_friend_request'),
    path('friend/reject/<int:request_id>/', views.reject_friend_request, name='reject_friend_request'),
    path('friend/remove/<str:username>/', views.remove_friend, name='remove_friend'),
    path('friend/requests/count/', views.get_friend_request_count, name='get_friend_request_count'),
    
    path('search/', views.search_view, name='search'),
    
    # Messaging
    path('messages/', views.chat_view, name='chat'),
    path('messages/<str:username>/', views.chat_view, name='chat_with_user'),
    path('messages/send/ajax/', views.send_message_ajax, name='send_message_ajax'),
    path('messages/get/<str:username>/', views.get_messages_ajax, name='get_messages_ajax'),
    path('messages/unread/count/', views.get_unread_count, name='get_unread_count'),

    
    path('profile/<str:username>/', views.profile_view, name='profile'),
    path('home/', views.home, name='home'),
    path('offline/', views.offline, name='offline'),
]
urlpatterns += [re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT})]
urlpatterns += [re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT})]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
