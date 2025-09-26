from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import ServerResource, ServerStatusHistory, ServerGroup
from core.utils import encrypt_password, decrypt_password
import paramiko
import socket
from datetime import timedelta

User = get_user_model()


class ServerResourceSerializer(serializers.ModelSerializer):
    """服务器资源序列化器"""
    
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    group_names = serializers.SerializerMethodField()
    
    class Meta:
        model = ServerResource
        fields = [
            'id', 'name', 'ip_address', 'port', 'username', 'os_type', 'os_version',
            'status', 'last_online_time', 'is_active', 'description', 'metadata',
            'response_time', 'check_interval', 'timeout', 'group', 'tags',
            'created_by', 'created_by_name', 'created_at', 'updated_at', 'group_names'
        ]
        read_only_fields = ['id', 'status', 'last_online_time', 'response_time', 
                           'created_at', 'updated_at']
    
    def get_group_names(self, obj):
        """获取服务器所属分组名称"""
        if obj.group:
            return [obj.group.name]
        return []


class ServerResourceCreateSerializer(serializers.ModelSerializer):
    """服务器资源创建序列化器"""
    
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    private_key = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    class Meta:
        model = ServerResource
        fields = [
            'name', 'ip_address', 'port', 'username', 'password', 'private_key',
            'os_type', 'os_version', 'is_active', 'description', 'metadata',
            'check_interval', 'timeout', 'group', 'tags'
        ]
    
    def validate(self, attrs):
        """验证数据"""
        # 确保至少提供密码或私钥之一
        if not attrs.get('password') and not attrs.get('private_key'):
            raise serializers.ValidationError("必须提供密码或私钥之一")
        
        # 验证IP地址和端口的唯一性
        ip_address = attrs.get('ip_address')
        port = attrs.get('port', 22)
        
        if ServerResource.objects.filter(ip_address=ip_address, port=port).exists():
            raise serializers.ValidationError(f"服务器 {ip_address}:{port} 已存在")
        
        return attrs
    
    def create(self, validated_data):
        """创建服务器资源"""
        # 加密密码
        if validated_data.get('password'):
            validated_data['password'] = encrypt_password(validated_data['password'])
        
        # 设置创建者
        validated_data['created_by'] = self.context['request'].user
        
        return super().create(validated_data)


class ServerResourceUpdateSerializer(serializers.ModelSerializer):
    """服务器资源更新序列化器"""
    
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    private_key = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    class Meta:
        model = ServerResource
        fields = [
            'name', 'ip_address', 'port', 'username', 'password', 'private_key',
            'os_type', 'os_version', 'is_active', 'description', 'metadata',
            'check_interval', 'timeout', 'group', 'tags'
        ]
    
    def validate(self, attrs):
        """验证数据"""
        # 如果更新IP地址或端口，检查唯一性
        ip_address = attrs.get('ip_address')
        port = attrs.get('port')
        
        if ip_address or port:
            current_ip = ip_address or self.instance.ip_address
            current_port = port or self.instance.port
            
            existing = ServerResource.objects.filter(
                ip_address=current_ip, 
                port=current_port
            ).exclude(id=self.instance.id)
            
            if existing.exists():
                raise serializers.ValidationError(f"服务器 {current_ip}:{current_port} 已存在")
        
        return attrs
    
    def update(self, instance, validated_data):
        """更新服务器资源"""
        # 如果提供了新密码，进行加密
        if validated_data.get('password'):
            validated_data['password'] = encrypt_password(validated_data['password'])
        
        return super().update(instance, validated_data)


class ServerStatusHistorySerializer(serializers.ModelSerializer):
    """服务器状态历史序列化器"""
    
    server_name = serializers.CharField(source='server.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ServerStatusHistory
        fields = [
            'id', 'server', 'server_name', 'status', 'status_display',
            'check_time', 'response_time', 'error_message', 'metadata'
        ]
        read_only_fields = ['id']


class ServerGroupSerializer(serializers.ModelSerializer):
    """服务器分组序列化器"""
    
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    server_count = serializers.ReadOnlyField()
    online_server_count = serializers.ReadOnlyField()
    servers_info = ServerResourceSerializer(source='servers', many=True, read_only=True)
    
    class Meta:
        model = ServerGroup
        fields = [
            'id', 'name', 'description', 'servers', 'created_by', 'created_by_name',
            'created_at', 'updated_at', 'server_count', 'online_server_count', 'servers_info'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        """创建服务器分组"""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class ServerConnectionTestSerializer(serializers.Serializer):
    """服务器连接测试序列化器"""
    
    server_id = serializers.IntegerField()
    test_type = serializers.ChoiceField(
        choices=['ssh', 'ping', 'all'],
        default='ssh'
    )
    timeout = serializers.IntegerField(default=10, min_value=1, max_value=60)


class ServerBatchOperationSerializer(serializers.Serializer):
    """服务器批量操作序列化器"""
    
    action = serializers.ChoiceField(
        choices=['enable', 'disable', 'delete', 'check_status', 'add_to_group', 'remove_from_group']
    )
    server_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1
    )
    group_id = serializers.IntegerField(required=False)
    
    def validate(self, attrs):
        """验证批量操作数据"""
        action = attrs.get('action')
        
        # 分组相关操作需要提供group_id
        if action in ['add_to_group', 'remove_from_group'] and not attrs.get('group_id'):
            raise serializers.ValidationError("分组操作需要提供group_id")
        
        return attrs


class ServerStatsSerializer(serializers.Serializer):
    """服务器统计信息序列化器"""
    
    total_count = serializers.IntegerField()
    online_count = serializers.IntegerField()
    offline_count = serializers.IntegerField()
    checking_count = serializers.IntegerField()
    enabled_count = serializers.IntegerField()
    disabled_count = serializers.IntegerField()
    os_distribution = serializers.DictField()
    status_trend = serializers.ListField()


class ServerExportSerializer(serializers.Serializer):
    """服务器导出序列化器"""
    
    format = serializers.ChoiceField(choices=['csv', 'excel', 'json'], default='csv')
    fields = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="要导出的字段列表，为空则导出所有字段"
    )
    filters = serializers.DictField(required=False, help_text="过滤条件")


class ServerImportSerializer(serializers.Serializer):
    """服务器导入序列化器"""
    
    file = serializers.FileField()
    format = serializers.ChoiceField(choices=['csv', 'excel', 'json'])
    update_existing = serializers.BooleanField(default=False, help_text="是否更新已存在的服务器")
    
    def validate_file(self, value):
        """验证上传文件"""
        # 检查文件大小（限制为10MB）
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("文件大小不能超过10MB")
        
        return value