from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
import paramiko
import socket
from typing import Dict, Any

from .models import ServerResource, ServerStatusHistory, ServerGroup
from .serializers import (
    ServerResourceSerializer, ServerResourceCreateSerializer, 
    ServerResourceUpdateSerializer, ServerStatusHistorySerializer,
    ServerGroupSerializer, ServerConnectionTestSerializer,
    ServerBatchOperationSerializer, ServerStatsSerializer,
    ServerExportSerializer, ServerImportSerializer
)
from core.utils import encrypt_password, decrypt_password


class ServerResourceViewSet(viewsets.ModelViewSet):
    """服务器资源管理视图集"""
    queryset = ServerResource.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """根据动作选择序列化器"""
        if self.action == 'create':
            return ServerResourceCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ServerResourceUpdateSerializer
        return ServerResourceSerializer
    
    def get_queryset(self):
        """获取查询集，支持过滤和搜索"""
        queryset = ServerResource.objects.all()
        
        # 状态过滤
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # 分组过滤
        group_id = self.request.query_params.get('group_id')
        if group_id:
            queryset = queryset.filter(group_id=group_id)
        
        # 操作系统过滤
        os_type = self.request.query_params.get('os_type')
        if os_type:
            queryset = queryset.filter(os_type=os_type)
        
        # 搜索
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(ip_address__icontains=search) |
                Q(description__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        """创建服务器资源时加密密码"""
        validated_data = serializer.validated_data
        if 'ssh_password' in validated_data and validated_data['ssh_password']:
            validated_data['ssh_password'] = encrypt_password(validated_data['ssh_password'])
        
        # 保存服务器
        server = serializer.save(created_by=self.request.user)
        
        # 立即进行状态检测
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)  # 2秒超时
            result = sock.connect_ex((server.ip_address, server.port))
            sock.close()
            
            if result == 0:
                server.status = 'online'
                server.last_online_time = timezone.now()
                status_msg = '在线'
            else:
                server.status = 'offline'
                status_msg = '离线'
            
            server.save()
            
            # 记录状态历史
            ServerStatusHistory.objects.create(
                server=server,
                status=server.status,
                changed_by=self.request.user,
                notes=f'创建服务器后状态检测: {status_msg}'
            )
        except Exception as e:
            # 如果检测失败，设为离线状态
            server.status = 'offline'
            server.save()
            
            ServerStatusHistory.objects.create(
                server=server,
                status='offline',
                changed_by=self.request.user,
                notes=f'创建服务器后状态检测失败: {str(e)}'
            )
    
    def perform_update(self, serializer):
        """更新服务器资源时处理密码加密"""
        validated_data = serializer.validated_data
        if 'ssh_password' in validated_data and validated_data['ssh_password']:
            # 如果密码有变化，重新加密
            instance = self.get_object()
            if validated_data['ssh_password'] != instance.ssh_password:
                validated_data['ssh_password'] = encrypt_password(validated_data['ssh_password'])
        serializer.save(updated_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """测试服务器连接"""
        server = self.get_object()
        
        try:
            # 创建SSH客户端
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # 准备连接参数
            connect_params = {
                'hostname': server.ip_address,
                'port': server.port,
                'username': server.username,
                'timeout': 10
            }
            
            # 根据认证方式添加参数
            if server.password:
                connect_params['password'] = decrypt_password(server.password)
            elif server.private_key:
                from io import StringIO
                private_key = paramiko.RSAKey.from_private_key(StringIO(server.private_key))
                connect_params['pkey'] = private_key
            else:
                return Response({
                    'success': False,
                    'message': '未配置密码或私钥'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 尝试连接
            ssh.connect(**connect_params)
            
            # 执行简单命令测试
            stdin, stdout, stderr = ssh.exec_command('echo "connection test"')
            result = stdout.read().decode().strip()
            
            ssh.close()
            
            # 更新服务器状态
            server.update_status('online')
            
            return Response({
                'success': True,
                'message': '连接成功',
                'result': result
            })
            
        except Exception as e:
            # 更新服务器状态为离线
            server.update_status('offline', error_message=str(e))
            
            return Response({
                'success': False,
                'message': f'连接失败: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def check_status(self, request, pk=None):
        """检查服务器状态"""
        server = self.get_object()
        
        try:
            # 使用socket进行简单的端口连通性测试
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)  # 2秒超时
            result = sock.connect_ex((server.ip_address, server.port))
            sock.close()
            
            if result == 0:
                # 端口可达，更新为在线状态
                server.status = 'online'
                server.last_online_time = timezone.now()
                server.save()
                
                # 记录状态历史
                ServerStatusHistory.objects.create(
                    server=server,
                    old_status=server.status,
                    new_status='online',
                    check_time=timezone.now()
                )
                
                return Response({
                    'success': True,
                    'status': 'online',
                    'message': '服务器在线'
                })
            else:
                # 端口不可达，更新为离线状态
                server.status = 'offline'
                server.save()
                
                # 记录状态历史
                ServerStatusHistory.objects.create(
                    server=server,
                    old_status=server.status,
                    new_status='offline',
                    check_time=timezone.now()
                )
                
                return Response({
                    'success': False,
                    'status': 'offline',
                    'message': '服务器离线'
                })
                
        except Exception as e:
            # 检查失败，更新为离线状态
            server.status = 'offline'
            server.save()
            
            # 记录状态历史
            ServerStatusHistory.objects.create(
                server=server,
                old_status=server.status,
                new_status='offline',
                error_message=str(e),
                check_time=timezone.now()
            )
            
            return Response({
                'success': False,
                'status': 'offline',
                'message': f'状态检查失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def batch_operation(self, request):
        """批量操作服务器"""
        operation = request.data.get('operation')
        server_ids = request.data.get('server_ids', [])
        
        if not operation or not server_ids:
            return Response({
                'success': False,
                'message': '缺少操作类型或服务器ID'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        servers = self.get_queryset().filter(id__in=server_ids)
        results = []
        
        for server in servers:
            try:
                if operation == 'check_status':
                    # 检查状态
                    import socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    result = sock.connect_ex((server.ip_address, server.port))
                    sock.close()
                    
                    if result == 0:
                        server.update_status('online')
                        results.append({
                            'id': server.id,
                            'name': server.name,
                            'success': True,
                            'status': 'online'
                        })
                    else:
                        server.update_status('offline')
                        results.append({
                            'id': server.id,
                            'name': server.name,
                            'success': True,
                            'status': 'offline'
                        })
                        
                elif operation == 'enable':
                    server.is_active = True
                    server.save()
                    results.append({
                        'id': server.id,
                        'name': server.name,
                        'success': True,
                        'message': '已启用'
                    })
                    
                elif operation == 'disable':
                    server.is_active = False
                    server.save()
                    results.append({
                        'id': server.id,
                        'name': server.name,
                        'success': True,
                        'message': '已禁用'
                    })
                    
                else:
                    results.append({
                        'id': server.id,
                        'name': server.name,
                        'success': False,
                        'message': '不支持的操作'
                    })
                    
            except Exception as e:
                results.append({
                    'id': server.id,
                    'name': server.name,
                    'success': False,
                    'message': str(e)
                })
        
        return Response({
            'success': True,
            'results': results
        })
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """获取服务器统计信息"""
        # 总数统计
        total_count = ServerResource.objects.count()
        online_count = ServerResource.objects.filter(status='online').count()
        offline_count = ServerResource.objects.filter(status='offline').count()
        checking_count = ServerResource.objects.filter(status='checking').count()
        
        # 按分组统计
        group_stats = ServerGroup.objects.annotate(
            server_count=Count('servers')
        ).values('id', 'name', 'server_count')
        
        # 按操作系统统计
        os_stats = ServerResource.objects.values('os_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # 最近7天新增服务器
        seven_days_ago = timezone.now() - timedelta(days=7)
        recent_count = ServerResource.objects.filter(
            created_at__gte=seven_days_ago
        ).count()
        
        return Response({
            'total_servers': total_count,
            'online_servers': online_count,
            'offline_servers': offline_count,
            'checking_servers': checking_count,
            'group_statistics': list(group_stats),
            'os_statistics': list(os_stats),
            'recent_additions': recent_count
        })


class ServerStatusHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """服务器状态历史视图集"""
    queryset = ServerStatusHistory.objects.all()
    serializer_class = ServerStatusHistorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """获取查询集，支持按服务器过滤"""
        queryset = ServerStatusHistory.objects.all()
        
        server_id = self.request.query_params.get('server_id')
        if server_id:
            queryset = queryset.filter(server_id=server_id)
        
        return queryset.order_by('-changed_at')


class ServerGroupViewSet(viewsets.ModelViewSet):
    """服务器分组视图集"""
    queryset = ServerGroup.objects.all()
    serializer_class = ServerGroupSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """获取查询集，支持搜索"""
        queryset = ServerGroup.objects.all()
        
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
        
        return queryset.order_by('name')
    
    def perform_create(self, serializer):
        """创建分组时设置创建者"""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def servers(self, request, pk=None):
        """获取分组下的所有服务器"""
        group = self.get_object()
        servers = group.servers.all()
        serializer = ServerResourceSerializer(servers, many=True)
        return Response(serializer.data)
