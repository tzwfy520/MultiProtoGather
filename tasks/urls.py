from django.urls import path
from . import views

app_name = 'tasks'

urlpatterns = [
    # Task Template URLs
    path('templates/', views.TaskTemplateListCreateView.as_view(), name='template-list-create'),
    path('templates/<int:pk>/', views.TaskTemplateDetailView.as_view(), name='template-detail'),
    
    # Collection Task URLs
    path('', views.CollectionTaskListCreateView.as_view(), name='task-list-create'),
    path('<int:pk>/', views.CollectionTaskDetailView.as_view(), name='task-detail'),
    
    # Task Execution URLs
    path('executions/', views.TaskExecutionListView.as_view(), name='execution-list'),
    
    # Task Batch Operations
    path('batch-operations/', views.TaskBatchOperationView.as_view(), name='batch-operations'),
    
    # Task Schedule Operations
    path('schedule/', views.TaskScheduleView.as_view(), name='task-schedule'),
    
    # Task Statistics
    path('stats/', views.task_stats, name='task-stats'),
    
    # Task Export/Import
    path('export/', views.TaskExportView.as_view(), name='task-export'),
    path('import/', views.TaskImportView.as_view(), name='task-import'),
]