from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.http import HttpResponse
from datetime import timedelta
import json
import csv
from .models import ServiceZone, Collector, CollectorPerformance, CollectorDeployment
from .serializers import (
    ServiceZoneSerializer, ServiceZoneCreateSerializer, ServiceZoneUpdateSerializer,
    CollectorSerializer, CollectorCreateSerializer, CollectorUpdateSerializer,
    CollectorPerformanceSerializer, CollectorDeploymentSerializer,
    CollectorDeploymentCreateSerializer, CollectorStatsSerializer,
    CollectorHeartbeatSerializer, CollectorBatchOperationSerializer,
    ServiceZoneConnectionTestSerializer, CollectorLogSerializer,
    CollectorExportSerializer
)
from users.models import OperationLog


class ServiceZoneListCreateView(generics.ListCreateAPIView):
    """服务区列表和创建视图"""
    queryset = ServiceZone.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ServiceZoneCreateSerializer
        return ServiceZoneSerializer
    
    def get_queryset(self):
        queryset = ServiceZone.objects.all()
        
        # 搜索过滤
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(server_ip__icontains=search)
            )
        
        # 状态过滤
        zone_status = self.request.query_params.get('status')
        if zone_status:
            queryset = queryset.filter(status=zone_status)
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        service_zone = serializer.save()
        
        # 记录操作日志
        OperationLog.objects.create(
            user=self.request.user,
            action='create',
            resource_type='service_zone',
            resource_id=service_zone.id,
            resource_name=service_zone.name,
            description=f'创建服务区: {service_zone.name} ({service_zone.server_ip})',
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


class ServiceZoneDetailView(generics.RetrieveUpdateDestroyAPIView):
    """服务区详情视图"""
    queryset = ServiceZone.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ServiceZoneUpdateSerializer
        return ServiceZoneSerializer
    
    def perform_update(self, serializer):
        service_zone = serializer.save()
        
        # 记录操作日志
        OperationLog.objects.create(
            user=self.request.user,
            action='update',
            resource_type='service_zone',
            resource_id=service_zone.id,
            resource_name=service_zone.name,
            description=f'更新服务区: {service_zone.name}',
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )
    
    def perform_destroy(self, instance):
        # 检查是否有关联的采集器
        if instance.collectors.exists():
            return Response(
                {"error": "无法删除包含采集器的服务区"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 记录操作日志
        OperationLog.objects.create(
            user=self.request.user,
            action='delete',
            resource_type='service_zone',
            resource_id=instance.id,
            resource_name=instance.name,
            description=f'删除服务区: {instance.name}',
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


class CollectorListCreateView(generics.ListCreateAPIView):
    """采集器列表和创建视图"""
    queryset = Collector.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CollectorCreateSerializer
        return CollectorSerializer
    
    def get_queryset(self):
        queryset = Collector.objects.select_related('service_zone').all()
        
        # 搜索过滤
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(collector_type__icontains=search) |
                Q(tags__icontains=search)
            )
        
        # 服务区过滤
        service_zone_id = self.request.query_params.get('service_zone')
        if service_zone_id:
            queryset = queryset.filter(service_zone_id=service_zone_id)
        
        # 类型过滤
        collector_type = self.request.query_params.get('type')
        if collector_type:
            queryset = queryset.filter(collector_type=collector_type)
        
        # 状态过滤
        collector_status = self.request.query_params.get('status')
        if collector_status:
            queryset = queryset.filter(status=collector_status)
        
        # 标签过滤
        tags = self.request.query_params.get('tags')
        if tags:
            tag_list = tags.split(',')
            for tag in tag_list:
                queryset = queryset.filter(tags__icontains=tag.strip())
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        collector = serializer.save()
        
        # 记录操作日志
        OperationLog.objects.create(
            user=self.request.user,
            action='create',
            resource_type='collector',
            resource_id=collector.id,
            resource_name=collector.name,
            description=f'创建采集器: {collector.name} ({collector.collector_type})',
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


class CollectorDetailView(generics.RetrieveUpdateDestroyAPIView):
    """采集器详情视图"""
    queryset = Collector.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return CollectorUpdateSerializer
        return CollectorSerializer
    
    def perform_update(self, serializer):
        collector = serializer.save()
        
        # 记录操作日志
        OperationLog.objects.create(
            user=self.request.user,
            action='update',
            resource_type='collector',
            resource_id=collector.id,
            resource_name=collector.name,
            description=f'更新采集器: {collector.name}',
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )
    
    def perform_destroy(self, instance):
        # 记录操作日志
        OperationLog.objects.create(
            user=self.request.user,
            action='delete',
            resource_type='collector',
            resource_id=instance.id,
            resource_name=instance.name,
            description=f'删除采集器: {instance.name}',
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


class CollectorPerformanceListView(generics.ListAPIView):
    """采集器性能历史列表视图"""
    serializer_class = CollectorPerformanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        collector_id = self.kwargs.get('collector_id')
        queryset = CollectorPerformance.objects.filter(collector_id=collector_id)
        
        # 时间范围过滤
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)
        
        return queryset.order_by('-timestamp')


class CollectorDeploymentListCreateView(generics.ListCreateAPIView):
    """采集器部署列表和创建视图"""
    queryset = CollectorDeployment.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CollectorDeploymentCreateSerializer
        return CollectorDeploymentSerializer
    
    def get_queryset(self):
        queryset = CollectorDeployment.objects.select_related('collector', 'service_zone').all()
        
        # 采集器过滤
        collector_id = self.request.query_params.get('collector')
        if collector_id:
            queryset = queryset.filter(collector_id=collector_id)
        
        # 服务区过滤
        service_zone_id = self.request.query_params.get('service_zone')
        if service_zone_id:
            queryset = queryset.filter(service_zone_id=service_zone_id)
        
        # 状态过滤
        deployment_status = self.request.query_params.get('status')
        if deployment_status:
            queryset = queryset.filter(status=deployment_status)
        
        return queryset.order_by('-deploy_time')
    
    def perform_create(self, serializer):
        deployment = serializer.save()
        
        # 这里应该触发实际的部署逻辑
        # 暂时设置为pending状态
        deployment.status = 'pending'
        deployment.save()
        
        # 记录操作日志
        OperationLog.objects.create(
            user=self.request.user,
            action='deploy',
            resource_type='collector',
            resource_id=deployment.collector.id,
            resource_name=deployment.collector.name,
            description=f'部署采集器: {deployment.collector.name} 到 {deployment.service_zone.name}',
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


class CollectorHeartbeatView(APIView):
    """采集器心跳视图"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = CollectorHeartbeatSerializer(data=request.data)
        if serializer.is_valid():
            collector_id = serializer.validated_data['collector_id']
            
            try:
                collector = Collector.objects.get(id=collector_id)
                
                # 更新采集器状态
                collector.status = serializer.validated_data['status']
                collector.last_heartbeat = timezone.now()
                
                # 更新性能指标
                if 'cpu_usage' in serializer.validated_data:
                    collector.cpu_usage = serializer.validated_data['cpu_usage']
                if 'memory_usage' in serializer.validated_data:
                    collector.memory_usage = serializer.validated_data['memory_usage']
                if 'task_count' in serializer.validated_data:
                    collector.task_count = serializer.validated_data['task_count']
                if 'success_rate' in serializer.validated_data:
                    collector.success_rate = serializer.validated_data['success_rate']
                if 'avg_response_time' in serializer.validated_data:
                    collector.avg_response_time = serializer.validated_data['avg_response_time']
                
                collector.save()
                
                # 记录性能历史
                CollectorPerformance.objects.create(
                    collector=collector,
                    cpu_usage=serializer.validated_data.get('cpu_usage', 0),
                    memory_usage=serializer.validated_data.get('memory_usage', 0),
                    task_count=serializer.validated_data.get('task_count', 0),
                    success_count=int(collector.task_count * collector.success_rate / 100) if collector.task_count and collector.success_rate else 0,
                    error_count=collector.task_count - int(collector.task_count * collector.success_rate / 100) if collector.task_count and collector.success_rate else 0,
                    avg_response_time=serializer.validated_data.get('avg_response_time', 0),
                    metadata=serializer.validated_data.get('metadata', {})
                )
                
                return Response({'status': 'success'})
                
            except Collector.DoesNotExist:
                return Response(
                    {"error": "采集器不存在"},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CollectorBatchOperationView(APIView):
    """采集器批量操作视图"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = CollectorBatchOperationSerializer(data=request.data)
        if serializer.is_valid():
            collector_ids = serializer.validated_data['collector_ids']
            operation = serializer.validated_data['operation']
            
            collectors = Collector.objects.filter(id__in=collector_ids)
            result = {'success': 0, 'failed': 0, 'errors': []}
            
            for collector in collectors:
                try:
                    if operation == 'start':
                        # 这里应该调用实际的启动逻辑
                        collector.status = 'online'
                        collector.save()
                    elif operation == 'stop':
                        # 这里应该调用实际的停止逻辑
                        collector.status = 'offline'
                        collector.save()
                    elif operation == 'restart':
                        # 这里应该调用实际的重启逻辑
                        collector.status = 'online'
                        collector.save()
                    elif operation == 'delete':
                        collector.delete()
                    elif operation == 'update_tags':
                        tags = serializer.validated_data['tags']
                        collector.tags = ','.join(tags)
                        collector.save()
                    
                    result['success'] += 1
                    
                except Exception as e:
                    result['failed'] += 1
                    result['errors'].append(f'采集器 {collector.name}: {str(e)}')
            
            # 记录操作日志
            OperationLog.objects.create(
                user=request.user,
                action='batch_operation',
                resource_type='collector',
                description=f'批量操作采集器: {operation}, 成功: {result["success"]}, 失败: {result["failed"]}',
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                metadata={'operation': operation, 'collector_count': len(collector_ids)}
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


class ServiceZoneConnectionTestView(APIView):
    """服务区连接测试视图"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ServiceZoneConnectionTestSerializer(data=request.data)
        if serializer.is_valid():
            service_zone_id = serializer.validated_data['service_zone_id']
            test_type = serializer.validated_data['test_type']
            
            try:
                service_zone = ServiceZone.objects.get(id=service_zone_id)
                test_result = self.test_service_zone_connection(service_zone, test_type)
                
                # 更新服务区状态
                service_zone.status = 'online' if test_result['success'] else 'offline'
                service_zone.last_heartbeat = timezone.now()
                service_zone.save()
                
                # 记录操作日志
                OperationLog.objects.create(
                    user=request.user,
                    action='test',
                    resource_type='service_zone',
                    resource_id=service_zone.id,
                    resource_name=service_zone.name,
                    description=f'测试服务区连接: {service_zone.name}',
                    ip_address=self.get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                
                return Response(test_result)
                
            except ServiceZone.DoesNotExist:
                return Response(
                    {"error": "服务区不存在"},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def test_service_zone_connection(self, service_zone, test_type):
        """测试服务区连接（模拟实现）"""
        import random
        import time
        
        # 模拟连接测试
        time.sleep(1)  # 模拟网络延迟
        
        success = random.choice([True, True, True, False])  # 75%成功率
        
        result = {
            'success': success,
            'test_time': timezone.now().isoformat(),
            'tests': {}
        }
        
        if test_type in ['ssh', 'all']:
            result['tests']['ssh'] = {
                'success': success,
                'response_time': random.uniform(100, 1000) if success else None,
                'error_message': None if success else "SSH连接失败"
            }
        
        if test_type in ['ping', 'all']:
            result['tests']['ping'] = {
                'success': success,
                'response_time': random.uniform(10, 100) if success else None,
                'error_message': None if success else "Ping超时"
            }
        
        return result
    
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
def collector_stats(request):
    """采集器统计视图"""
    # 基础统计
    total_collectors = Collector.objects.count()
    online_collectors = Collector.objects.filter(status='online').count()
    offline_collectors = Collector.objects.filter(status='offline').count()
    busy_collectors = Collector.objects.filter(status='busy').count()
    
    # 类型统计
    type_stats = dict(Collector.objects.values('collector_type').annotate(count=Count('collector_type')))
    
    # 服务区统计
    service_zone_stats = {}
    for zone in ServiceZone.objects.all():
        service_zone_stats[zone.name] = zone.collectors.count()
    
    # 性能趋势（最近7天）
    performance_trend = []
    for i in range(7):
        date = timezone.now().date() - timedelta(days=i)
        daily_performance = CollectorPerformance.objects.filter(
            timestamp__date=date
        ).aggregate(
            avg_cpu=Avg('cpu_usage'),
            avg_memory=Avg('memory_usage'),
            total_tasks=Count('task_count'),
            avg_response_time=Avg('avg_response_time')
        )
        
        trend_data = {
            'date': date.isoformat(),
            'avg_cpu': daily_performance['avg_cpu'] or 0,
            'avg_memory': daily_performance['avg_memory'] or 0,
            'total_tasks': daily_performance['total_tasks'] or 0,
            'avg_response_time': daily_performance['avg_response_time'] or 0
        }
        
        performance_trend.append(trend_data)
    
    stats_data = {
        'total_collectors': total_collectors,
        'online_collectors': online_collectors,
        'offline_collectors': offline_collectors,
        'busy_collectors': busy_collectors,
        'type_stats': type_stats,
        'service_zone_stats': service_zone_stats,
        'performance_trend': performance_trend,
    }
    
    serializer = CollectorStatsSerializer(stats_data)
    return Response(serializer.data)


class CollectorExportView(APIView):
    """采集器导出视图"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = CollectorExportSerializer(data=request.data)
        if serializer.is_valid():
            export_format = serializer.validated_data['format']
            fields = serializer.validated_data.get('fields')
            service_zone_ids = serializer.validated_data.get('service_zone_ids')
            collector_types = serializer.validated_data.get('collector_types')
            status_list = serializer.validated_data.get('status')
            
            # 构建查询集
            queryset = Collector.objects.select_related('service_zone').all()
            
            if service_zone_ids:
                queryset = queryset.filter(service_zone_id__in=service_zone_ids)
            if collector_types:
                queryset = queryset.filter(collector_type__in=collector_types)
            if status_list:
                queryset = queryset.filter(status__in=status_list)
            
            # 导出数据
            if export_format == 'csv':
                return self.export_csv(queryset, fields)
            elif export_format == 'json':
                return self.export_json(queryset, fields)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def export_csv(self, queryset, fields):
        """导出CSV格式"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="collectors.csv"'
        
        writer = csv.writer(response)
        
        # 写入表头
        if not fields:
            fields = ['name', 'collector_type', 'version', 'service_zone_name', 'status', 'cpu_usage', 'memory_usage']
        
        writer.writerow(fields)
        
        # 写入数据
        for collector in queryset:
            row = []
            for field in fields:
                if field == 'service_zone_name':
                    value = collector.service_zone.name if collector.service_zone else ''
                else:
                    value = getattr(collector, field, '')
                row.append(str(value))
            writer.writerow(row)
        
        return response
    
    def export_json(self, queryset, fields):
        """导出JSON格式"""
        data = []
        for collector in queryset:
            collector_data = {}
            if not fields:
                fields = ['id', 'name', 'collector_type', 'version', 'status', 'cpu_usage', 'memory_usage']
            
            for field in fields:
                if field == 'service_zone_name':
                    collector_data[field] = collector.service_zone.name if collector.service_zone else ''
                else:
                    collector_data[field] = getattr(collector, field, '')
            
            data.append(collector_data)
        
        response = HttpResponse(
            json.dumps(data, ensure_ascii=False, indent=2),
            content_type='application/json'
        )
        response['Content-Disposition'] = 'attachment; filename="collectors.json"'
        
        return response
