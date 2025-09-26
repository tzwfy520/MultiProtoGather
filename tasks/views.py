from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.http import HttpResponse
from datetime import timedelta, datetime
import json
import csv
import pandas as pd
from .models import TaskTemplate, CollectionTask, TaskExecution
from .serializers import (
    TaskTemplateSerializer, CollectionTaskSerializer, CollectionTaskCreateSerializer,
    CollectionTaskUpdateSerializer, TaskExecutionSerializer, TaskBatchOperationSerializer,
    TaskStatsSerializer, TaskExportSerializer, TaskImportSerializer,
    TaskScheduleSerializer, TaskLogSerializer
)
from users.models import OperationLog


class TaskTemplateListCreateView(generics.ListCreateAPIView):
    """任务模板列表和创建视图"""
    queryset = TaskTemplate.objects.all()
    serializer_class = TaskTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = TaskTemplate.objects.all()
        
        # 搜索过滤
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(protocol__icontains=search)
            )
        
        # 协议过滤
        protocol = self.request.query_params.get('protocol')
        if protocol:
            queryset = queryset.filter(protocol=protocol)
        
        # 是否启用过滤
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        template = serializer.save()
        
        # 记录操作日志
        OperationLog.objects.create(
            user=self.request.user,
            action='create',
            resource_type='task_template',
            resource_id=template.id,
            resource_name=template.name,
            description=f'创建任务模板: {template.name} ({template.protocol})',
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )
    
    def get_client_ip(self):
        """获取客户端IP地址"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class TaskTemplateDetailView(generics.RetrieveUpdateDestroyAPIView):
    """任务模板详情视图"""
    queryset = TaskTemplate.objects.all()
    serializer_class = TaskTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_update(self, serializer):
        template = serializer.save()
        
        # 记录操作日志
        OperationLog.objects.create(
            user=self.request.user,
            action='update',
            resource_type='task_template',
            resource_id=template.id,
            resource_name=template.name,
            description=f'更新任务模板: {template.name}',
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )
    
    def perform_destroy(self, instance):
        # 检查是否有关联的任务
        if instance.tasks.exists():
            return Response(
                {"error": "无法删除包含关联任务的模板"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 记录操作日志
        OperationLog.objects.create(
            user=self.request.user,
            action='delete',
            resource_type='task_template',
            resource_id=instance.id,
            resource_name=instance.name,
            description=f'删除任务模板: {instance.name}',
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )
        
        instance.delete()
    
    def get_client_ip(self):
        """获取客户端IP地址"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class CollectionTaskListCreateView(generics.ListCreateAPIView):
    """采集任务列表和创建视图"""
    queryset = CollectionTask.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CollectionTaskCreateSerializer
        return CollectionTaskSerializer
    
    def get_queryset(self):
        queryset = CollectionTask.objects.select_related('template', 'collector').prefetch_related('target_devices', 'target_groups').all()
        
        # 搜索过滤
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(template__name__icontains=search)
            )
        
        # 模板过滤
        template_id = self.request.query_params.get('template')
        if template_id:
            queryset = queryset.filter(template_id=template_id)
        
        # 采集器过滤
        collector_id = self.request.query_params.get('collector')
        if collector_id:
            queryset = queryset.filter(collector_id=collector_id)
        
        # 状态过滤
        task_status = self.request.query_params.get('status')
        if task_status:
            queryset = queryset.filter(status=task_status)
        
        # 优先级过滤
        priority = self.request.query_params.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)
        
        # 是否启用过滤
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        task = serializer.save()
        
        # 这里应该调用XXL-Job API创建任务
        # 暂时模拟设置XXL-Job任务ID
        task.xxl_job_id = f"job_{task.id}_{timezone.now().timestamp()}"
        task.save()
        
        # 记录操作日志
        OperationLog.objects.create(
            user=self.request.user,
            action='create',
            resource_type='collection_task',
            resource_id=task.id,
            resource_name=task.name,
            description=f'创建采集任务: {task.name}',
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )
    
    def get_client_ip(self):
        """获取客户端IP地址"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class CollectionTaskDetailView(generics.RetrieveUpdateDestroyAPIView):
    """采集任务详情视图"""
    queryset = CollectionTask.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return CollectionTaskUpdateSerializer
        return CollectionTaskSerializer
    
    def perform_update(self, serializer):
        task = serializer.save()
        
        # 这里应该调用XXL-Job API更新任务
        
        # 记录操作日志
        OperationLog.objects.create(
            user=self.request.user,
            action='update',
            resource_type='collection_task',
            resource_id=task.id,
            resource_name=task.name,
            description=f'更新采集任务: {task.name}',
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )
    
    def perform_destroy(self, instance):
        # 这里应该调用XXL-Job API删除任务
        
        # 记录操作日志
        OperationLog.objects.create(
            user=self.request.user,
            action='delete',
            resource_type='collection_task',
            resource_id=instance.id,
            resource_name=instance.name,
            description=f'删除采集任务: {instance.name}',
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )
        
        instance.delete()
    
    def get_client_ip(self):
        """获取客户端IP地址"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class TaskExecutionListView(generics.ListAPIView):
    """任务执行记录列表视图"""
    serializer_class = TaskExecutionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = TaskExecution.objects.select_related('task', 'collector').all()
        
        # 任务过滤
        task_id = self.request.query_params.get('task')
        if task_id:
            queryset = queryset.filter(task_id=task_id)
        
        # 采集器过滤
        collector_id = self.request.query_params.get('collector')
        if collector_id:
            queryset = queryset.filter(collector_id=collector_id)
        
        # 状态过滤
        execution_status = self.request.query_params.get('status')
        if execution_status:
            queryset = queryset.filter(status=execution_status)
        
        # 时间范围过滤
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(start_time__gte=start_date)
        if end_date:
            queryset = queryset.filter(start_time__lte=end_date)
        
        return queryset.order_by('-start_time')


class TaskBatchOperationView(APIView):
    """任务批量操作视图"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = TaskBatchOperationSerializer(data=request.data)
        if serializer.is_valid():
            task_ids = serializer.validated_data['task_ids']
            operation = serializer.validated_data['operation']
            
            tasks = CollectionTask.objects.filter(id__in=task_ids)
            result = {'success': 0, 'failed': 0, 'errors': []}
            
            for task in tasks:
                try:
                    if operation == 'start':
                        # 这里应该调用XXL-Job API启动任务
                        task.status = 'running'
                        task.is_active = True
                        task.save()
                    elif operation == 'stop':
                        # 这里应该调用XXL-Job API停止任务
                        task.status = 'stopped'
                        task.save()
                    elif operation == 'enable':
                        task.is_active = True
                        task.save()
                    elif operation == 'disable':
                        task.is_active = False
                        task.save()
                    elif operation == 'delete':
                        # 这里应该调用XXL-Job API删除任务
                        task.delete()
                    
                    result['success'] += 1
                    
                except Exception as e:
                    result['failed'] += 1
                    result['errors'].append(f'任务 {task.name}: {str(e)}')
            
            # 记录操作日志
            OperationLog.objects.create(
                user=request.user,
                action='batch_operation',
                resource_type='collection_task',
                description=f'批量操作任务: {operation}, 成功: {result["success"]}, 失败: {result["failed"]}',
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                metadata={'operation': operation, 'task_count': len(task_ids)}
            )
            
            return Response(result)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get_client_ip(self, request):
        """获取客户端IP地址"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class TaskScheduleView(APIView):
    """任务调度视图"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = TaskScheduleSerializer(data=request.data)
        if serializer.is_valid():
            task_id = serializer.validated_data['task_id']
            action = serializer.validated_data['action']
            schedule_time = serializer.validated_data.get('schedule_time')
            
            try:
                task = CollectionTask.objects.get(id=task_id)
                
                # 这里应该调用XXL-Job API进行任务调度
                if action == 'start':
                    task.status = 'running'
                    task.last_run_time = timezone.now()
                elif action == 'stop':
                    task.status = 'stopped'
                elif action == 'pause':
                    task.status = 'paused'
                elif action == 'resume':
                    task.status = 'running'
                
                task.save()
                
                # 记录操作日志
                OperationLog.objects.create(
                    user=request.user,
                    action='schedule',
                    resource_type='collection_task',
                    resource_id=task.id,
                    resource_name=task.name,
                    description=f'调度任务: {task.name} - {action}',
                    ip_address=self.get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                
                return Response({'status': 'success', 'message': f'任务{action}成功'})
                
            except CollectionTask.DoesNotExist:
                return Response(
                    {"error": "任务不存在"},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get_client_ip(self, request):
        """获取客户端IP地址"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def task_stats(request):
    """任务统计视图"""
    # 基础统计
    total_tasks = CollectionTask.objects.count()
    active_tasks = CollectionTask.objects.filter(is_active=True).count()
    paused_tasks = CollectionTask.objects.filter(status='paused').count()
    
    # 执行统计
    completed_executions = TaskExecution.objects.filter(status='success').count()
    failed_executions = TaskExecution.objects.filter(status='failed').count()
    
    # 状态统计
    status_stats = dict(CollectionTask.objects.values('status').annotate(count=Count('status')))
    
    # 优先级统计
    priority_stats = dict(CollectionTask.objects.values('priority').annotate(count=Count('priority')))
    
    # 模板统计
    template_stats = {}
    for template in TaskTemplate.objects.all():
        template_stats[template.name] = template.tasks.count()
    
    # 执行趋势（最近7天）
    execution_trend = []
    for i in range(7):
        date = timezone.now().date() - timedelta(days=i)
        daily_executions = TaskExecution.objects.filter(
            start_time__date=date
        ).aggregate(
            total=Count('id'),
            success=Count('id', filter=Q(status='success')),
            failed=Count('id', filter=Q(status='failed'))
        )
        
        trend_data = {
            'date': date.isoformat(),
            'total': daily_executions['total'] or 0,
            'success': daily_executions['success'] or 0,
            'failed': daily_executions['failed'] or 0,
            'success_rate': (daily_executions['success'] / daily_executions['total'] * 100) if daily_executions['total'] else 0
        }
        
        execution_trend.append(trend_data)
    
    # 成功率趋势
    success_rate_trend = []
    for i in range(7):
        date = timezone.now().date() - timedelta(days=i)
        daily_stats = TaskExecution.objects.filter(
            start_time__date=date
        ).aggregate(
            total=Count('id'),
            success=Count('id', filter=Q(status='success'))
        )
        
        success_rate = (daily_stats['success'] / daily_stats['total'] * 100) if daily_stats['total'] else 0
        success_rate_trend.append({
            'date': date.isoformat(),
            'success_rate': success_rate
        })
    
    stats_data = {
        'total_tasks': total_tasks,
        'active_tasks': active_tasks,
        'paused_tasks': paused_tasks,
        'completed_tasks': completed_executions,
        'failed_tasks': failed_executions,
        'status_stats': status_stats,
        'type_stats': template_stats,
        'priority_stats': priority_stats,
        'execution_trend': execution_trend,
        'success_rate_trend': success_rate_trend,
    }
    
    serializer = TaskStatsSerializer(stats_data)
    return Response(serializer.data)


class TaskExportView(APIView):
    """任务导出视图"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = TaskExportSerializer(data=request.data)
        if serializer.is_valid():
            export_format = serializer.validated_data['format']
            fields = serializer.validated_data.get('fields')
            template_ids = serializer.validated_data.get('template_ids')
            collector_ids = serializer.validated_data.get('collector_ids')
            status_list = serializer.validated_data.get('status')
            priority_list = serializer.validated_data.get('priority')
            
            # 构建查询集
            queryset = CollectionTask.objects.select_related('template', 'collector').all()
            
            if template_ids:
                queryset = queryset.filter(template_id__in=template_ids)
            if collector_ids:
                queryset = queryset.filter(collector_id__in=collector_ids)
            if status_list:
                queryset = queryset.filter(status__in=status_list)
            if priority_list:
                queryset = queryset.filter(priority__in=priority_list)
            
            # 导出数据
            if export_format == 'csv':
                return self.export_csv(queryset, fields)
            elif export_format == 'json':
                return self.export_json(queryset, fields)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def export_csv(self, queryset, fields):
        """导出CSV格式"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="tasks.csv"'
        
        writer = csv.writer(response)
        
        # 写入表头
        if not fields:
            fields = ['name', 'template_name', 'collector_name', 'status', 'priority', 'is_active']
        
        writer.writerow(fields)
        
        # 写入数据
        for task in queryset:
            row = []
            for field in fields:
                if field == 'template_name':
                    value = task.template.name if task.template else ''
                elif field == 'collector_name':
                    value = task.collector.name if task.collector else ''
                else:
                    value = getattr(task, field, '')
                row.append(str(value))
            writer.writerow(row)
        
        return response
    
    def export_json(self, queryset, fields):
        """导出JSON格式"""
        data = []
        for task in queryset:
            task_data = {}
            if not fields:
                fields = ['id', 'name', 'status', 'priority', 'is_active']
            
            for field in fields:
                if field == 'template_name':
                    task_data[field] = task.template.name if task.template else ''
                elif field == 'collector_name':
                    task_data[field] = task.collector.name if task.collector else ''
                else:
                    task_data[field] = getattr(task, field, '')
            
            data.append(task_data)
        
        response = HttpResponse(
            json.dumps(data, ensure_ascii=False, indent=2),
            content_type='application/json'
        )
        response['Content-Disposition'] = 'attachment; filename="tasks.json"'
        
        return response


class TaskImportView(APIView):
    """任务导入视图"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = TaskImportSerializer(data=request.data)
        if serializer.is_valid():
            file = serializer.validated_data['file']
            update_existing = serializer.validated_data['update_existing']
            default_template_id = serializer.validated_data.get('default_template_id')
            default_collector_id = serializer.validated_data.get('default_collector_id')
            
            try:
                # 读取文件
                if file.name.endswith('.csv'):
                    df = pd.read_csv(file)
                else:
                    df = pd.read_excel(file)
                
                result = {'success': 0, 'failed': 0, 'errors': []}
                
                for index, row in df.iterrows():
                    try:
                        # 验证必需字段
                        if pd.isna(row.get('name')):
                            result['errors'].append(f'第{index+2}行: 任务名称不能为空')
                            result['failed'] += 1
                            continue
                        
                        # 检查任务是否已存在
                        task_name = row['name']
                        existing_task = CollectionTask.objects.filter(name=task_name).first()
                        
                        if existing_task and not update_existing:
                            result['errors'].append(f'第{index+2}行: 任务 {task_name} 已存在')
                            result['failed'] += 1
                            continue
                        
                        # 准备任务数据
                        task_data = {
                            'name': task_name,
                            'description': row.get('description', ''),
                            'priority': row.get('priority', 'medium'),
                            'is_active': row.get('is_active', True),
                            'template_id': row.get('template_id', default_template_id),
                            'collector_id': row.get('collector_id', default_collector_id),
                        }
                        
                        # 创建或更新任务
                        if existing_task and update_existing:
                            for key, value in task_data.items():
                                if value is not None:
                                    setattr(existing_task, key, value)
                            existing_task.save()
                        else:
                            CollectionTask.objects.create(**task_data)
                        
                        result['success'] += 1
                        
                    except Exception as e:
                        result['failed'] += 1
                        result['errors'].append(f'第{index+2}行: {str(e)}')
                
                # 记录操作日志
                OperationLog.objects.create(
                    user=request.user,
                    action='import',
                    resource_type='collection_task',
                    description=f'导入任务: 成功 {result["success"]}, 失败 {result["failed"]}',
                    ip_address=self.get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    metadata={'file_name': file.name, 'total_rows': len(df)}
                )
                
                return Response(result)
                
            except Exception as e:
                return Response(
                    {"error": f"文件处理失败: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get_client_ip(self, request):
        """获取客户端IP地址"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
