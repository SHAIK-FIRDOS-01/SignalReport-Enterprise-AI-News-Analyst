from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('apps.accounts.urls')),
    path('social-auth/', include('social_django.urls', namespace='social')),
    path('', include('apps.knowledge_base.urls')),
]
