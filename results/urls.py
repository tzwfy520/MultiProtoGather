from django.urls import path
from . import views

app_name = 'results'

urlpatterns = [
    # 采集结果相关URL
    path('collection-results/', views.CollectionResultListView.as_view(), name='collection-result-list'),
    path('collection-results/<int:pk>/', views.CollectionResultDetailView.as_view(), name='collection-result-detail'),
    
    # 结果分析相关URL
    path('analysis/', views.ResultAnalysisListCreateView.as_view(), name='result-analysis-list'),
    path('analysis/<int:pk>/', views.ResultAnalysisDetailView.as_view(), name='result-analysis-detail'),
    
    # 数据导出相关URL
    path('exports/', views.DataExportListCreateView.as_view(), name='data-export-list'),
    path('exports/<int:pk>/', views.DataExportDetailView.as_view(), name='data-export-detail'),
    path('exports/<int:pk>/download/', views.DataExportDownloadView.as_view(), name='data-export-download'),
    
    # 批量操作
    path('batch-operation/', views.ResultBatchOperationView.as_view(), name='result-batch-operation'),
    
    # 统计信息
    path('stats/', views.result_stats, name='result-stats'),
    
    # 导出功能
    path('export/', views.ResultExportView.as_view(), name='result-export'),
]