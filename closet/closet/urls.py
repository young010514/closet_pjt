<<<<<<< HEAD
from django.contrib import admin
from django.urls import include, path

=======
"""
URL configuration for closet project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
>>>>>>> 237d073ad7f444fbd928a85215bc8eb9e94c9c6b

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/accounts/", include("accounts.urls")),
<<<<<<< HEAD
    path("api/community/", include("community.urls")),
    path("api/regions/", include("regions.urls")),
    path("api/stores/", include("stores.urls")),
]
=======
    path('api/community/', include("community.urls")),
    path('regions/', include("regions.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
>>>>>>> 237d073ad7f444fbd928a85215bc8eb9e94c9c6b
