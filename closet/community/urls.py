from django.urls import path
from . import views

urlpatterns = [
    path('posts/', views.PostListCreateView.as_view(), name='post-list'),
    path('posts/<int:pk>/', views.PostDetailView.as_view(), name='post-detail'),
    path('posts/<int:pk>/like/', views.PostLikeView.as_view(), name='post-like'),
    path('posts/<int:pk>/apply/', views.ExperienceApplicationView.as_view(), name='post-apply'),
    path('posts/<int:pk>/comments/', views.CommentListCreateView.as_view(), name='comment-list'),
    path('posts/<int:pk>/comments/<int:comment_pk>/', views.CommentDetailView.as_view(), name='comment-detail'),
]
