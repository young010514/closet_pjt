from django.urls import path

from . import views

urlpatterns = [
    path('dashboard/', views.DashboardView.as_view(), name='business-dashboard'),
    path('store/posts/', views.StorePostListCreateView.as_view(), name='store-post-list'),
    path('store/posts/<int:pk>/', views.StorePostDetailView.as_view(), name='store-post-detail'),
    path('experience/posts/', views.ExperiencePostListCreateView.as_view(), name='experience-post-list'),
    path('experience/posts/<int:pk>/', views.ExperiencePostDetailView.as_view(), name='experience-post-detail'),
    path('experience/posts/<int:pk>/applicants/', views.ExperienceApplicantListView.as_view(), name='experience-applicants'),
]
