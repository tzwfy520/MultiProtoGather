from django.urls import path
from . import views

app_name = 'devices'

urlpatterns = [
    # 设备分组相关
    path('groups/', views.DeviceGroupListCreateView.as_view(), name='group-list-create'),
    path('groups/<int:pk>/', views.DeviceGroupDetailView.as_view(), name='group-detail'),
    
    # 设备相关
    path('', views.DeviceListCreateView.as_view(), name='device-list-create'),
    path('<int:pk>/', views.DeviceDetailView.as_view(), name='device-detail'),
    path('<int:device_id>/status-history/', views.DeviceStatusHistoryListView.as_view(), name='device-status-history'),
    
    # 设备操作
    path('test-connection/', views.DeviceConnectionTestView.as_view(), name='device-test-connection'),
    path('batch-operation/', views.DeviceBatchOperationView.as_view(), name='device-batch-operation'),
    
    # 设备统计
    path('stats/', views.device_stats, name='device-stats'),
    
    # 设备导入导出
    path('export/', views.DeviceExportView.as_view(), name='device-export'),
    path('import/', views.DeviceImportView.as_view(), name='device-import'),
]