"""
URL configuration for multiprotgather_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
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
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Django管理后台
    path("admin/", admin.site.urls),
    
    # API路由
    path('api/v1/users/', include('users.urls')),
    path('api/v1/devices/', include('devices.urls')),
    path('api/v1/collectors/', include('collectors.urls')),
    path('api/v1/tasks/', include('tasks.urls')),
    path('api/v1/alerts/', include('alerts.urls')),
    path('api/v1/results/', include('results.urls')),
    path('api/v1/resources/', include('resources.urls')),  # 新增的服务器资源管理API
]

# 开发环境下提供静态文件和媒体文件服务
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
