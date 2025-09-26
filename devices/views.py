from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q, Count
from django.utils import timezone
from django.http import HttpResponse
from datetime import timedelta
import json
import csv
import io
from .models import DeviceGroup, Device, DeviceStatusHistory
from .serializers import (
    DeviceGroupSerializer, DeviceSerializer, DeviceCreateSerializer,
    DeviceUpdateSerializer, DeviceStatusHistorySerializer,
    DeviceConnectionTestSerializer, DeviceBatchOperationSerializer,
    DeviceStatsSerializer, DeviceExportSerializer, DeviceImportSerializer
)
from users.models import OperationLog


class DeviceGroupListCreateView(generics.ListCreateAPIView):
    """设备分组列表和创建视图"""
    queryset = DeviceGroup.objects.all()
    serializer_class = DeviceGroupSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = DeviceGroup.objects.filter(parent__isnull=True)  # 只返回根分组
        
        # 搜索过滤
        search = self.request.query_params.get('search')
        if search:
            queryset = DeviceGroup.objects.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
        
        return queryset.order_by('name')
    
    def perform_create(self, serializer):
        group = serializer.save()
        
        # 记录操作日志
        OperationLog.objects.create(
            user=self.request.user,
            action='create',
            resource_type='device_group',
            resource_id=group.id,
            resource_name=group.name,
            description=f'创建设备分组: {group.name}',
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


class DeviceGroupDetailView(generics.RetrieveUpdateDestroyAPIView):
    """设备分组详情视图"""
    queryset = DeviceGroup.objects.all()
    serializer_class = DeviceGroupSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_update(self, serializer):
        group = serializer.save()
        
        # 记录操作日志
        OperationLog.objects.create(
            user=self.request.user,
            action='update',
            resource_type='device_group',
            resource_id=group.id,
            resource_name=group.name,
            description=f'更新设备分组: {group.name}',
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )
    
    def perform_destroy(self, instance):
        # 检查是否有子分组或设备
        if instance.children.exists():
            return Response(
                {"error": "无法删除包含子分组的分组"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if instance.devices.exists():
            return Response(
                {"error": "无法删除包含设备的分组"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 记录操作日志
        OperationLog.objects.create(
            user=self.request.user,
            action='delete',
            resource_type='device_group',
            resource_id=instance.id,
            resource_name=instance.name,
            description=f'删除设备分组: {instance.name}',
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


class DeviceListCreateView(generics.ListCreateAPIView):
    """设备列表和创建视图"""
    queryset = Device.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return DeviceCreateSerializer
        return DeviceSerializer
    
    def get_queryset(self):
        queryset = Device.objects.select_related('group').all()
        
        # 搜索过滤
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(ip_address__icontains=search) |
                Q(description__icontains=search) |
                Q(tags__icontains=search)
            )
        
        # 分组过滤
        group_id = self.request.query_params.get('group')
        if group_id:
            queryset = queryset.filter(group_id=group_id)
        
        # 协议过滤
        protocol = self.request.query_params.get('protocol')
        if protocol:
            queryset = queryset.filter(protocol=protocol)
        
        # 状态过滤
        device_status = self.request.query_params.get('status')
        if device_status:
            queryset = queryset.filter(status=device_status)
        
        # 标签过滤
        tags = self.request.query_params.get('tags')
        if tags:
            tag_list = tags.split(',')
            for tag in tag_list:
                queryset = queryset.filter(tags__icontains=tag.strip())
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        device = serializer.save()
        
        # 记录操作日志
        OperationLog.objects.create(
            user=self.request.user,
            action='create',
            resource_type='device',
            resource_id=device.id,
            resource_name=device.name,
            description=f'创建设备: {device.name} ({device.ip_address})',
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


class DeviceDetailView(generics.RetrieveUpdateDestroyAPIView):
    """设备详情视图"""
    queryset = Device.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return DeviceUpdateSerializer
        return DeviceSerializer
    
    def perform_update(self, serializer):
        device = serializer.save()
        
        # 记录操作日志
        OperationLog.objects.create(
            user=self.request.user,
            action='update',
            resource_type='device',
            resource_id=device.id,
            resource_name=device.name,
            description=f'更新设备: {device.name} ({device.ip_address})',
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )
    
    def perform_destroy(self, instance):
        # 记录操作日志
        OperationLog.objects.create(
            user=self.request.user,
            action='delete',
            resource_type='device',
            resource_id=instance.id,
            resource_name=instance.name,
            description=f'删除设备: {instance.name} ({instance.ip_address})',
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


class DeviceStatusHistoryListView(generics.ListAPIView):
    """设备状态历史列表视图"""
    serializer_class = DeviceStatusHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        device_id = self.kwargs.get('device_id')
        queryset = DeviceStatusHistory.objects.filter(device_id=device_id)
        
        # 时间范围过滤
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(check_time__gte=start_date)
        if end_date:
            queryset = queryset.filter(check_time__lte=end_date)
        
        # 状态过滤
        device_status = self.request.query_params.get('status')
        if device_status:
            queryset = queryset.filter(status=device_status)
        
        return queryset.order_by('-check_time')


class DeviceConnectionTestView(APIView):
    """设备连接测试视图"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = DeviceConnectionTestSerializer(data=request.data)
        if serializer.is_valid():
            device_id = serializer.validated_data['device_id']
            device = Device.objects.get(id=device_id)
            
            # 这里应该调用实际的连接测试逻辑
            # 暂时返回模拟结果
            test_result = self.test_device_connection(device)
            
            # 记录测试结果到状态历史
            DeviceStatusHistory.objects.create(
                device=device,
                status='online' if test_result['success'] else 'offline',
                response_time=test_result.get('response_time'),
                error_message=test_result.get('error_message'),
                metadata={'test_type': 'manual', 'user_id': request.user.id}
            )
            
            # 更新设备状态
            device.status = 'online' if test_result['success'] else 'offline'
            device.last_check_time = timezone.now()
            device.save()
            
            # 记录操作日志
            OperationLog.objects.create(
                user=request.user,
                action='test',
                resource_type='device',
                resource_id=device.id,
                resource_name=device.name,
                description=f'测试设备连接: {device.name}',
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return Response(test_result)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def test_device_connection(self, device):
        """测试设备连接（模拟实现）"""
        import random
        import time
        
        # 模拟连接测试
        time.sleep(0.5)  # 模拟网络延迟
        
        success = random.choice([True, True, True, False])  # 75%成功率
        response_time = random.uniform(10, 500) if success else None
        error_message = None if success else "连接超时"
        
        return {
            'success': success,
            'response_time': response_time,
            'error_message': error_message,
            'test_time': timezone.now().isoformat()
        }
    
    def get_client_ip(self, request):
        """获取客户端IP地址"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class DeviceBatchOperationView(APIView):
    """设备批量操作视图"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = DeviceBatchOperationSerializer(data=request.data)
        if serializer.is_valid():
            device_ids = serializer.validated_data['device_ids']
            operation = serializer.validated_data['operation']
            
            devices = Device.objects.filter(id__in=device_ids)
            result = {'success': 0, 'failed': 0, 'errors': []}
            
            for device in devices:
                try:
                    if operation == 'delete':
                        device.delete()
                    elif operation == 'enable':
                        device.status = 'online'
                        device.save()
                    elif operation == 'disable':
                        device.status = 'offline'
                        device.save()
                    elif operation == 'move_group':
                        target_group_id = serializer.validated_data['target_group_id']
                        device.group_id = target_group_id
                        device.save()
                    elif operation == 'add_tags':
                        tags = serializer.validated_data['tags']
                        existing_tags = device.tags.split(',') if device.tags else []
                        new_tags = list(set(existing_tags + tags))
                        device.tags = ','.join(new_tags)
                        device.save()
                    elif operation == 'remove_tags':
                        tags = serializer.validated_data['tags']
                        existing_tags = device.tags.split(',') if device.tags else []
                        remaining_tags = [tag for tag in existing_tags if tag not in tags]
                        device.tags = ','.join(remaining_tags)
                        device.save()
                    
                    result['success'] += 1
                    
                except Exception as e:
                    result['failed'] += 1
                    result['errors'].append(f'设备 {device.name}: {str(e)}')
            
            # 记录操作日志
            OperationLog.objects.create(
                user=request.user,
                action='batch_operation',
                resource_type='device',
                description=f'批量操作设备: {operation}, 成功: {result["success"]}, 失败: {result["failed"]}',
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                metadata={'operation': operation, 'device_count': len(device_ids)}
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


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def device_stats(request):
    """设备统计视图"""
    # 基础统计
    total_devices = Device.objects.count()
    online_devices = Device.objects.filter(status='online').count()
    offline_devices = Device.objects.filter(status='offline').count()
    unknown_devices = Device.objects.filter(status='unknown').count()
    
    # 协议统计
    protocol_stats = dict(Device.objects.values('protocol').annotate(count=Count('protocol')))
    
    # 分组统计
    group_stats = {}
    for group in DeviceGroup.objects.all():
        group_stats[group.name] = group.devices.count()
    
    # 状态趋势（最近7天）
    status_trend = []
    for i in range(7):
        date = timezone.now().date() - timedelta(days=i)
        daily_stats = DeviceStatusHistory.objects.filter(
            check_time__date=date
        ).values('status').annotate(count=Count('status'))
        
        trend_data = {'date': date.isoformat()}
        for stat in daily_stats:
            trend_data[stat['status']] = stat['count']
        
        status_trend.append(trend_data)
    
    stats_data = {
        'total_devices': total_devices,
        'online_devices': online_devices,
        'offline_devices': offline_devices,
        'unknown_devices': unknown_devices,
        'protocol_stats': protocol_stats,
        'group_stats': group_stats,
        'status_trend': status_trend,
    }
    
    serializer = DeviceStatsSerializer(stats_data)
    return Response(serializer.data)


class DeviceExportView(APIView):
    """设备导出视图"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = DeviceExportSerializer(data=request.data)
        if serializer.is_valid():
            export_format = serializer.validated_data['format']
            fields = serializer.validated_data.get('fields')
            group_ids = serializer.validated_data.get('group_ids')
            protocols = serializer.validated_data.get('protocols')
            status_list = serializer.validated_data.get('status')
            
            # 构建查询集
            queryset = Device.objects.select_related('group').all()
            
            if group_ids:
                queryset = queryset.filter(group_id__in=group_ids)
            if protocols:
                queryset = queryset.filter(protocol__in=protocols)
            if status_list:
                queryset = queryset.filter(status__in=status_list)
            
            # 导出数据
            if export_format == 'csv':
                return self.export_csv(queryset, fields)
            elif export_format == 'json':
                return self.export_json(queryset, fields)
            else:
                return Response(
                    {"error": "暂不支持该导出格式"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def export_csv(self, queryset, fields):
        """导出CSV格式"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="devices.csv"'
        
        writer = csv.writer(response)
        
        # 写入表头
        if not fields:
            fields = ['name', 'ip_address', 'port', 'protocol', 'group_name', 'status', 'description']
        
        writer.writerow(fields)
        
        # 写入数据
        for device in queryset:
            row = []
            for field in fields:
                if field == 'group_name':
                    value = device.group.name if device.group else ''
                else:
                    value = getattr(device, field, '')
                row.append(str(value))
            writer.writerow(row)
        
        return response
    
    def export_json(self, queryset, fields):
        """导出JSON格式"""
        data = []
        for device in queryset:
            device_data = {}
            if not fields:
                fields = ['id', 'name', 'ip_address', 'port', 'protocol', 'status', 'description']
            
            for field in fields:
                if field == 'group_name':
                    device_data[field] = device.group.name if device.group else ''
                else:
                    device_data[field] = getattr(device, field, '')
            
            data.append(device_data)
        
        response = HttpResponse(
            json.dumps(data, ensure_ascii=False, indent=2),
            content_type='application/json'
        )
        response['Content-Disposition'] = 'attachment; filename="devices.json"'
        
        return response


class DeviceImportView(APIView):
    """设备导入视图"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = DeviceImportSerializer(data=request.data)
        if serializer.is_valid():
            file = serializer.validated_data['file']
            update_existing = serializer.validated_data['update_existing']
            default_group_id = serializer.validated_data.get('default_group_id')
            
            try:
                result = self.import_devices(file, update_existing, default_group_id, request.user)
                return Response(result)
            except Exception as e:
                return Response(
                    {"error": f"导入失败: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def import_devices(self, file, update_existing, default_group_id, user):
        """导入设备数据"""
        import pandas as pd
        
        # 读取文件
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
        
        result = {'success': 0, 'failed': 0, 'updated': 0, 'errors': []}
        
        for index, row in df.iterrows():
            try:
                # 必需字段验证
                if pd.isna(row.get('name')) or pd.isna(row.get('ip_address')):
                    result['errors'].append(f'第{index+2}行: 设备名称和IP地址不能为空')
                    result['failed'] += 1
                    continue
                
                # 检查设备是否已存在
                existing_device = Device.objects.filter(ip_address=row['ip_address']).first()
                
                if existing_device and update_existing:
                    # 更新现有设备
                    self.update_device_from_row(existing_device, row, default_group_id)
                    result['updated'] += 1
                elif existing_device:
                    result['errors'].append(f'第{index+2}行: 设备IP {row["ip_address"]} 已存在')
                    result['failed'] += 1
                else:
                    # 创建新设备
                    self.create_device_from_row(row, default_group_id)
                    result['success'] += 1
                    
            except Exception as e:
                result['errors'].append(f'第{index+2}行: {str(e)}')
                result['failed'] += 1
        
        # 记录操作日志
        OperationLog.objects.create(
            user=user,
            action='import',
            resource_type='device',
            description=f'导入设备: 成功{result["success"]}, 更新{result["updated"]}, 失败{result["failed"]}',
            ip_address=self.get_client_ip(user),
            user_agent='',
            metadata=result
        )
        
        return result
    
    def create_device_from_row(self, row, default_group_id):
        """从行数据创建设备"""
        device_data = {
            'name': row['name'],
            'ip_address': row['ip_address'],
            'port': int(row.get('port', 22)),
            'protocol': row.get('protocol', 'ssh'),
            'username': row.get('username', ''),
            'description': row.get('description', ''),
            'tags': row.get('tags', ''),
            'group_id': default_group_id
        }
        
        device = Device(**device_data)
        
        # 处理密码
        if not pd.isna(row.get('password')):
            device.set_password(row['password'])
        
        device.save()
        return device
    
    def update_device_from_row(self, device, row, default_group_id):
        """从行数据更新设备"""
        device.name = row['name']
        device.port = int(row.get('port', device.port))
        device.protocol = row.get('protocol', device.protocol)
        device.username = row.get('username', device.username)
        device.description = row.get('description', device.description)
        device.tags = row.get('tags', device.tags)
        
        if default_group_id:
            device.group_id = default_group_id
        
        # 处理密码
        if not pd.isna(row.get('password')):
            device.set_password(row['password'])
        
        device.save()
        return device
    
    def get_client_ip(self, request):
        """获取客户端IP地址"""
        return '127.0.0.1'  # 导入操作的IP地址
