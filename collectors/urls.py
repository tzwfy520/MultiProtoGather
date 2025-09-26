from django.urls import path
from . import views

app_name = 'collectors'

urlpatterns = [
    # 服务区管理
    path('service-zones/', views.ServiceZoneListCreateView.as_view(), name='service-zone-list-create'),
    path('service-zones/<int:pk>/', views.ServiceZoneDetailView.as_view(), name='service-zone-detail'),
    path('service-zones/test-connection/', views.ServiceZoneConnectionTestView.as_view(), name='service-zone-test-connection'),
    
    # 采集器管理
    path('collectors/', views.CollectorListCreateView.as_view(), name='collector-list-create'),
    path('collectors/<int:pk>/', views.CollectorDetailView.as_view(), name='collector-detail'),
    path('collectors/stats/', views.collector_stats, name='collector-stats'),
    path('collectors/heartbeat/', views.CollectorHeartbeatView.as_view(), name='collector-heartbeat'),
    path('collectors/batch-operation/', views.CollectorBatchOperationView.as_view(), name='collector-batch-operation'),
    path('collectors/export/', views.CollectorExportView.as_view(), name='collector-export'),
    
    # 采集器性能
    path('collectors/<int:collector_id>/performance/', views.CollectorPerformanceListView.as_view(), name='collector-performance'),
    
    # 采集器部署
    path('deployments/', views.CollectorDeploymentListCreateView.as_view(), name='deployment-list-create'),
]