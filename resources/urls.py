from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# 创建路由器
router = DefaultRouter()

# 注册视图集
router.register(r'servers', views.ServerResourceViewSet, basename='server-resource')
router.register(r'server-history', views.ServerStatusHistoryViewSet, basename='server-history')
router.register(r'groups', views.ServerGroupViewSet, basename='server-group')

# URL配置
urlpatterns = [
    path('', include(router.urls)),
]

# 为了兼容前端现有的API调用，添加别名路由
urlpatterns += [
    # 兼容前端现有的 /resources/servers/ 路径
    path('servers/', include([
        path('', views.ServerResourceViewSet.as_view({'get': 'list', 'post': 'create'}), name='server-list'),
        path('<int:pk>/', views.ServerResourceViewSet.as_view({
            'get': 'retrieve', 
            'put': 'update', 
            'patch': 'partial_update', 
            'delete': 'destroy'
        }), name='server-detail'),
        path('<int:pk>/test-connection/', views.ServerResourceViewSet.as_view({'post': 'test_connection'}), name='server-test-connection'),
        path('<int:pk>/check-status/', views.ServerResourceViewSet.as_view({'post': 'check_status'}), name='server-check-status'),
        path('batch-operation/', views.ServerResourceViewSet.as_view({'post': 'batch_operation'}), name='server-batch-operation'),
        path('statistics/', views.ServerResourceViewSet.as_view({'get': 'statistics'}), name='server-statistics'),
    ])),
]