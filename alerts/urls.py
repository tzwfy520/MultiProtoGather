from django.urls import path
from . import views

app_name = 'alerts'

urlpatterns = [
    # 告警规则管理
    path('rules/', views.AlertRuleListCreateView.as_view(), name='alert-rule-list'),
    path('rules/<int:pk>/', views.AlertRuleDetailView.as_view(), name='alert-rule-detail'),
    
    # 告警记录管理
    path('alerts/', views.AlertListView.as_view(), name='alert-list'),
    path('alerts/<int:pk>/', views.AlertDetailView.as_view(), name='alert-detail'),
    path('alerts/acknowledge/', views.AlertAcknowledgeView.as_view(), name='alert-acknowledge'),
    path('alerts/resolve/', views.AlertResolveView.as_view(), name='alert-resolve'),
    path('alerts/batch-operation/', views.AlertBatchOperationView.as_view(), name='alert-batch-operation'),
    path('alerts/export/', views.AlertExportView.as_view(), name='alert-export'),
    
    # 通知渠道管理
    path('channels/', views.NotificationChannelListCreateView.as_view(), name='notification-channel-list'),
    path('channels/<int:pk>/', views.NotificationChannelDetailView.as_view(), name='notification-channel-detail'),
    
    # 通知日志
    path('notifications/', views.NotificationLogListView.as_view(), name='notification-log-list'),
    
    # 统计信息
    path('stats/', views.alert_stats, name='alert-stats'),
]