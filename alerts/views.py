from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q, Count
from django.utils import timezone
from django.http import HttpResponse
from datetime import datetime, timedelta
import csv
import json
import io

from .models import AlertRule, Alert, NotificationChannel, NotificationLog
from .serializers import (
    AlertRuleSerializer, AlertRuleCreateSerializer, AlertRuleUpdateSerializer,
    AlertSerializer, AlertAcknowledgeSerializer, AlertResolveSerializer,
    NotificationChannelSerializer, NotificationLogSerializer,
    AlertStatsSerializer, AlertBatchOperationSerializer, AlertExportSerializer
)
from users.models import OperationLog


def get_client_ip(request):
    """获取客户端IP地址"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class AlertRuleListCreateView(generics.ListCreateAPIView):
    """告警规则列表和创建视图"""
    queryset = AlertRule.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AlertRuleCreateSerializer
        return AlertRuleSerializer
    
    def get_queryset(self):
        queryset = AlertRule.objects.all()
        
        # 搜索
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
        
        # 过滤
        rule_type = self.request.query_params.get('rule_type')
        if rule_type:
            queryset = queryset.filter(rule_type=rule_type)
        
        severity = self.request.query_params.get('severity')
        if severity:
            queryset = queryset.filter(severity=severity)
        
        enabled = self.request.query_params.get('enabled')
        if enabled is not None:
            queryset = queryset.filter(enabled=enabled.lower() == 'true')
        
        return queryset
    
    def perform_create(self, serializer):
        rule = serializer.save()
        
        # 记录操作日志
        OperationLog.objects.create(
            user=self.request.user,
            action='create',
            resource_type='alert_rule',
            resource_id=rule.id,
            resource_name=rule.name,
            description=f"创建告警规则: {rule.name}",
            ip_address=get_client_ip(self.request),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )


class AlertRuleDetailView(generics.RetrieveUpdateDestroyAPIView):
    """告警规则详情视图"""
    queryset = AlertRule.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return AlertRuleUpdateSerializer
        return AlertRuleSerializer
    
    def perform_update(self, serializer):
        rule = serializer.save()
        
        # 记录操作日志
        OperationLog.objects.create(
            user=self.request.user,
            action='update',
            resource_type='alert_rule',
            resource_id=rule.id,
            resource_name=rule.name,
            description=f"更新告警规则: {rule.name}",
            ip_address=get_client_ip(self.request),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )
    
    def perform_destroy(self, instance):
        # 检查是否有关联的活跃告警
        active_alerts = Alert.objects.filter(
            rule=instance,
            status__in=['active', 'acknowledged']
        ).count()
        
        if active_alerts > 0:
            raise serializers.ValidationError(
                f"无法删除规则，存在 {active_alerts} 个活跃告警"
            )
        
        rule_name = instance.name
        rule_id = instance.id
        
        instance.delete()
        
        # 记录操作日志
        OperationLog.objects.create(
            user=self.request.user,
            action='delete',
            resource_type='alert_rule',
            resource_id=rule_id,
            resource_name=rule_name,
            description=f"删除告警规则: {rule_name}",
            ip_address=get_client_ip(self.request),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )


class AlertListView(generics.ListAPIView):
    """告警记录列表视图"""
    queryset = Alert.objects.all()
    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Alert.objects.select_related(
            'rule', 'task', 'device', 'acknowledged_by', 'resolved_by'
        )
        
        # 搜索
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(message__icontains=search) |
                Q(rule__name__icontains=search) |
                Q(device__name__icontains=search)
            )
        
        # 过滤
        rule_id = self.request.query_params.get('rule_id')
        if rule_id:
            queryset = queryset.filter(rule_id=rule_id)
        
        severity = self.request.query_params.get('severity')
        if severity:
            queryset = queryset.filter(severity=severity)
        
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        device_id = self.request.query_params.get('device_id')
        if device_id:
            queryset = queryset.filter(device_id=device_id)
        
        task_id = self.request.query_params.get('task_id')
        if task_id:
            queryset = queryset.filter(task_id=task_id)
        
        # 时间范围过滤
        start_time = self.request.query_params.get('start_time')
        if start_time:
            try:
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                queryset = queryset.filter(first_occurred_at__gte=start_time)
            except ValueError:
                pass
        
        end_time = self.request.query_params.get('end_time')
        if end_time:
            try:
                end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                queryset = queryset.filter(first_occurred_at__lte=end_time)
            except ValueError:
                pass
        
        return queryset


class AlertDetailView(generics.RetrieveAPIView):
    """告警记录详情视图"""
    queryset = Alert.objects.all()
    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated]


class AlertAcknowledgeView(APIView):
    """告警确认视图"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = AlertAcknowledgeSerializer(data=request.data)
        if serializer.is_valid():
            alert_ids = serializer.validated_data['alert_ids']
            comment = serializer.validated_data.get('comment', '')
            
            # 批量确认告警
            alerts = Alert.objects.filter(
                id__in=alert_ids,
                status='active'
            )
            
            acknowledged_count = 0
            for alert in alerts:
                alert.acknowledge(request.user)
                acknowledged_count += 1
            
            # 记录操作日志
            OperationLog.objects.create(
                user=request.user,
                action='acknowledge',
                resource_type='alert',
                resource_id=None,
                resource_name=f"{acknowledged_count}个告警",
                description=f"确认 {acknowledged_count} 个告警" + (f": {comment}" if comment else ""),
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return Response({
                'message': f'成功确认 {acknowledged_count} 个告警',
                'acknowledged_count': acknowledged_count
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AlertResolveView(APIView):
    """告警解决视图"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = AlertResolveSerializer(data=request.data)
        if serializer.is_valid():
            alert_ids = serializer.validated_data['alert_ids']
            comment = serializer.validated_data.get('comment', '')
            
            # 批量解决告警
            alerts = Alert.objects.filter(
                id__in=alert_ids,
                status__in=['active', 'acknowledged']
            )
            
            resolved_count = 0
            for alert in alerts:
                alert.resolve(request.user)
                resolved_count += 1
            
            # 记录操作日志
            OperationLog.objects.create(
                user=request.user,
                action='resolve',
                resource_type='alert',
                resource_id=None,
                resource_name=f"{resolved_count}个告警",
                description=f"解决 {resolved_count} 个告警" + (f": {comment}" if comment else ""),
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return Response({
                'message': f'成功解决 {resolved_count} 个告警',
                'resolved_count': resolved_count
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AlertBatchOperationView(APIView):
    """告警批量操作视图"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = AlertBatchOperationSerializer(data=request.data)
        if serializer.is_valid():
            operation = serializer.validated_data['operation']
            alert_ids = serializer.validated_data['alert_ids']
            comment = serializer.validated_data.get('comment', '')
            
            alerts = Alert.objects.filter(id__in=alert_ids)
            success_count = 0
            
            if operation == 'acknowledge':
                for alert in alerts.filter(status='active'):
                    alert.acknowledge(request.user)
                    success_count += 1
            
            elif operation == 'resolve':
                for alert in alerts.filter(status__in=['active', 'acknowledged']):
                    alert.resolve(request.user)
                    success_count += 1
            
            elif operation == 'delete':
                success_count = alerts.count()
                alerts.delete()
            
            # 记录操作日志
            OperationLog.objects.create(
                user=request.user,
                action=operation,
                resource_type='alert',
                resource_id=None,
                resource_name=f"{success_count}个告警",
                description=f"批量{operation} {success_count} 个告警" + (f": {comment}" if comment else ""),
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return Response({
                'message': f'成功{operation} {success_count} 个告警',
                'success_count': success_count
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NotificationChannelListCreateView(generics.ListCreateAPIView):
    """通知渠道列表和创建视图"""
    queryset = NotificationChannel.objects.all()
    serializer_class = NotificationChannelSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = NotificationChannel.objects.all()
        
        # 搜索
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
        
        # 过滤
        channel_type = self.request.query_params.get('channel_type')
        if channel_type:
            queryset = queryset.filter(channel_type=channel_type)
        
        enabled = self.request.query_params.get('enabled')
        if enabled is not None:
            queryset = queryset.filter(enabled=enabled.lower() == 'true')
        
        return queryset
    
    def perform_create(self, serializer):
        channel = serializer.save()
        
        # 记录操作日志
        OperationLog.objects.create(
            user=self.request.user,
            action='create',
            resource_type='notification_channel',
            resource_id=channel.id,
            resource_name=channel.name,
            description=f"创建通知渠道: {channel.name}",
            ip_address=get_client_ip(self.request),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )


class NotificationChannelDetailView(generics.RetrieveUpdateDestroyAPIView):
    """通知渠道详情视图"""
    queryset = NotificationChannel.objects.all()
    serializer_class = NotificationChannelSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_update(self, serializer):
        channel = serializer.save()
        
        # 记录操作日志
        OperationLog.objects.create(
            user=self.request.user,
            action='update',
            resource_type='notification_channel',
            resource_id=channel.id,
            resource_name=channel.name,
            description=f"更新通知渠道: {channel.name}",
            ip_address=get_client_ip(self.request),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )
    
    def perform_destroy(self, instance):
        channel_name = instance.name
        channel_id = instance.id
        
        instance.delete()
        
        # 记录操作日志
        OperationLog.objects.create(
            user=self.request.user,
            action='delete',
            resource_type='notification_channel',
            resource_id=channel_id,
            resource_name=channel_name,
            description=f"删除通知渠道: {channel_name}",
            ip_address=get_client_ip(self.request),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )


class NotificationLogListView(generics.ListAPIView):
    """通知日志列表视图"""
    queryset = NotificationLog.objects.all()
    serializer_class = NotificationLogSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = NotificationLog.objects.select_related(
            'alert', 'channel'
        )
        
        # 过滤
        alert_id = self.request.query_params.get('alert_id')
        if alert_id:
            queryset = queryset.filter(alert_id=alert_id)
        
        channel_id = self.request.query_params.get('channel_id')
        if channel_id:
            queryset = queryset.filter(channel_id=channel_id)
        
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # 时间范围过滤
        start_time = self.request.query_params.get('start_time')
        if start_time:
            try:
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                queryset = queryset.filter(created_at__gte=start_time)
            except ValueError:
                pass
        
        end_time = self.request.query_params.get('end_time')
        if end_time:
            try:
                end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                queryset = queryset.filter(created_at__lte=end_time)
            except ValueError:
                pass
        
        return queryset


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def alert_stats(request):
    """告警统计API"""
    now = timezone.now()
    
    # 基础统计
    total_alerts = Alert.objects.count()
    active_alerts = Alert.objects.filter(status='active').count()
    acknowledged_alerts = Alert.objects.filter(status='acknowledged').count()
    resolved_alerts = Alert.objects.filter(status='resolved').count()
    suppressed_alerts = Alert.objects.filter(status='suppressed').count()
    
    # 按级别统计
    critical_alerts = Alert.objects.filter(severity='critical').count()
    high_alerts = Alert.objects.filter(severity='high').count()
    medium_alerts = Alert.objects.filter(severity='medium').count()
    low_alerts = Alert.objects.filter(severity='low').count()
    info_alerts = Alert.objects.filter(severity='info').count()
    
    # 按规则类型统计
    threshold_alerts = Alert.objects.filter(rule__rule_type='threshold').count()
    pattern_alerts = Alert.objects.filter(rule__rule_type='pattern').count()
    anomaly_alerts = Alert.objects.filter(rule__rule_type='anomaly').count()
    status_alerts = Alert.objects.filter(rule__rule_type='status').count()
    timeout_alerts = Alert.objects.filter(rule__rule_type='timeout').count()
    
    # 7天趋势
    daily_trends = []
    for i in range(7):
        date = now.date() - timedelta(days=i)
        start_time = timezone.make_aware(datetime.combine(date, datetime.min.time()))
        end_time = start_time + timedelta(days=1)
        
        daily_count = Alert.objects.filter(
            first_occurred_at__gte=start_time,
            first_occurred_at__lt=end_time
        ).count()
        
        daily_trends.append({
            'date': date.strftime('%Y-%m-%d'),
            'count': daily_count
        })
    
    daily_trends.reverse()  # 按时间正序
    
    stats_data = {
        'total_alerts': total_alerts,
        'active_alerts': active_alerts,
        'acknowledged_alerts': acknowledged_alerts,
        'resolved_alerts': resolved_alerts,
        'suppressed_alerts': suppressed_alerts,
        'critical_alerts': critical_alerts,
        'high_alerts': high_alerts,
        'medium_alerts': medium_alerts,
        'low_alerts': low_alerts,
        'info_alerts': info_alerts,
        'threshold_alerts': threshold_alerts,
        'pattern_alerts': pattern_alerts,
        'anomaly_alerts': anomaly_alerts,
        'status_alerts': status_alerts,
        'timeout_alerts': timeout_alerts,
        'daily_trends': daily_trends
    }
    
    serializer = AlertStatsSerializer(stats_data)
    return Response(serializer.data)


class AlertExportView(APIView):
    """告警导出视图"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = AlertExportSerializer(data=request.data)
        if serializer.is_valid():
            # 构建查询集
            queryset = Alert.objects.select_related('rule', 'task', 'device')
            
            # 应用过滤条件
            if serializer.validated_data.get('rule_id'):
                queryset = queryset.filter(rule_id=serializer.validated_data['rule_id'])
            
            if serializer.validated_data.get('severity'):
                queryset = queryset.filter(severity=serializer.validated_data['severity'])
            
            if serializer.validated_data.get('status'):
                queryset = queryset.filter(status=serializer.validated_data['status'])
            
            if serializer.validated_data.get('device_id'):
                queryset = queryset.filter(device_id=serializer.validated_data['device_id'])
            
            if serializer.validated_data.get('task_id'):
                queryset = queryset.filter(task_id=serializer.validated_data['task_id'])
            
            if serializer.validated_data.get('start_time'):
                queryset = queryset.filter(first_occurred_at__gte=serializer.validated_data['start_time'])
            
            if serializer.validated_data.get('end_time'):
                queryset = queryset.filter(first_occurred_at__lte=serializer.validated_data['end_time'])
            
            export_format = serializer.validated_data.get('format', 'csv')
            
            if export_format == 'csv':
                return self._export_csv(queryset)
            else:
                return self._export_json(queryset)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def _export_csv(self, queryset):
        """导出CSV格式"""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入表头
        writer.writerow([
            'ID', '告警规则', '任务名称', '设备名称', '设备IP',
            '告警标题', '告警级别', '告警状态', '首次发生时间',
            '最后发生时间', '发生次数', '确认人', '解决人'
        ])
        
        # 写入数据
        for alert in queryset:
            writer.writerow([
                alert.id,
                alert.rule.name,
                alert.task.name if alert.task else '',
                alert.device.name if alert.device else '',
                alert.device.ip_address if alert.device else '',
                alert.title,
                alert.get_severity_display(),
                alert.get_status_display(),
                alert.first_occurred_at.strftime('%Y-%m-%d %H:%M:%S'),
                alert.last_occurred_at.strftime('%Y-%m-%d %H:%M:%S'),
                alert.occurrence_count,
                alert.acknowledged_by.username if alert.acknowledged_by else '',
                alert.resolved_by.username if alert.resolved_by else ''
            ])
        
        output.seek(0)
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="alerts_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        # 记录操作日志
        OperationLog.objects.create(
            user=self.request.user,
            action='export',
            resource_type='alert',
            resource_id=None,
            resource_name='告警数据',
            description=f"导出 {queryset.count()} 条告警数据(CSV格式)",
            ip_address=get_client_ip(self.request),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )
        
        return response
    
    def _export_json(self, queryset):
        """导出JSON格式"""
        alerts_data = []
        for alert in queryset:
            alerts_data.append({
                'id': alert.id,
                'rule_name': alert.rule.name,
                'task_name': alert.task.name if alert.task else None,
                'device_name': alert.device.name if alert.device else None,
                'device_ip': alert.device.ip_address if alert.device else None,
                'title': alert.title,
                'message': alert.message,
                'severity': alert.severity,
                'status': alert.status,
                'first_occurred_at': alert.first_occurred_at.isoformat(),
                'last_occurred_at': alert.last_occurred_at.isoformat(),
                'occurrence_count': alert.occurrence_count,
                'acknowledged_by': alert.acknowledged_by.username if alert.acknowledged_by else None,
                'resolved_by': alert.resolved_by.username if alert.resolved_by else None,
                'trigger_data': alert.trigger_data,
                'context_data': alert.context_data
            })
        
        response = HttpResponse(
            json.dumps(alerts_data, ensure_ascii=False, indent=2),
            content_type='application/json'
        )
        response['Content-Disposition'] = f'attachment; filename="alerts_{timezone.now().strftime("%Y%m%d_%H%M%S")}.json"'
        
        # 记录操作日志
        OperationLog.objects.create(
            user=self.request.user,
            action='export',
            resource_type='alert',
            resource_id=None,
            resource_name='告警数据',
            description=f"导出 {len(alerts_data)} 条告警数据(JSON格式)",
            ip_address=get_client_ip(self.request),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )
        
        return response
