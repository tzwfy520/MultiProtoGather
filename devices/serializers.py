from rest_framework import serializers
from django.utils import timezone
from .models import DeviceGroup, Device, DeviceStatusHistory


class DeviceGroupSerializer(serializers.ModelSerializer):
    """设备分组序列化器"""
    children = serializers.SerializerMethodField()
    device_count = serializers.SerializerMethodField()
    
    class Meta:
        model = DeviceGroup
        fields = ['id', 'name', 'description', 'parent', 'children', 'device_count', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
    
    def get_children(self, obj):
        """获取子分组"""
        children = obj.children.all()
        return DeviceGroupSerializer(children, many=True).data
    
    def get_device_count(self, obj):
        """获取分组下设备数量"""
        return obj.devices.count()


class DeviceSerializer(serializers.ModelSerializer):
    """设备序列化器"""
    group_name = serializers.CharField(source='group.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    protocol_display = serializers.CharField(source='get_protocol_display', read_only=True)
    
    # 敏感字段写入时不返回
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    private_key = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    class Meta:
        model = Device
        fields = [
            'id', 'name', 'ip_address', 'port', 'protocol', 'protocol_display',
            'username', 'password', 'private_key', 'group', 'group_name',
            'status', 'status_display', 'tags', 'description', 'metadata',
            'last_check_time', 'created_at', 'updated_at'
        ]
        read_only_fields = ['last_check_time', 'created_at', 'updated_at']
    
    def validate_ip_address(self, value):
        """验证IP地址格式"""
        import ipaddress
        try:
            ipaddress.ip_address(value)
        except ValueError:
            raise serializers.ValidationError("请输入有效的IP地址")
        return value
    
    def validate_port(self, value):
        """验证端口范围"""
        if not (1 <= value <= 65535):
            raise serializers.ValidationError("端口号必须在1-65535之间")
        return value
    
    def validate(self, attrs):
        """验证设备配置"""
        protocol = attrs.get('protocol')
        username = attrs.get('username')
        password = attrs.get('password')
        private_key = attrs.get('private_key')
        
        # SSH协议需要用户名和密码或私钥
        if protocol == 'ssh':
            if not username:
                raise serializers.ValidationError("SSH协议需要用户名")
            if not password and not private_key:
                raise serializers.ValidationError("SSH协议需要密码或私钥")
        
        # SNMP协议需要community字符串（存储在password字段）
        elif protocol == 'snmp':
            if not password:
                raise serializers.ValidationError("SNMP协议需要Community字符串")
        
        return attrs


class DeviceCreateSerializer(DeviceSerializer):
    """设备创建序列化器"""
    
    def create(self, validated_data):
        """创建设备时加密敏感信息"""
        device = Device(**validated_data)
        
        # 加密敏感字段
        if validated_data.get('password'):
            device.set_password(validated_data['password'])
        if validated_data.get('private_key'):
            device.set_private_key(validated_data['private_key'])
        
        device.save()
        return device


class DeviceUpdateSerializer(DeviceSerializer):
    """设备更新序列化器"""
    
    def update(self, instance, validated_data):
        """更新设备时处理敏感信息"""
        # 处理密码更新
        if 'password' in validated_data:
            password = validated_data.pop('password')
            if password:
                instance.set_password(password)
        
        # 处理私钥更新
        if 'private_key' in validated_data:
            private_key = validated_data.pop('private_key')
            if private_key:
                instance.set_private_key(private_key)
        
        # 更新其他字段
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance


class DeviceStatusHistorySerializer(serializers.ModelSerializer):
    """设备状态历史序列化器"""
    device_name = serializers.CharField(source='device.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = DeviceStatusHistory
        fields = [
            'id', 'device', 'device_name', 'status', 'status_display',
            'check_time', 'response_time', 'error_message', 'metadata'
        ]
        read_only_fields = ['check_time']


class DeviceConnectionTestSerializer(serializers.Serializer):
    """设备连接测试序列化器"""
    device_id = serializers.IntegerField()
    
    def validate_device_id(self, value):
        """验证设备是否存在"""
        try:
            Device.objects.get(id=value)
        except Device.DoesNotExist:
            raise serializers.ValidationError("设备不存在")
        return value


class DeviceBatchOperationSerializer(serializers.Serializer):
    """设备批量操作序列化器"""
    device_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=100
    )
    operation = serializers.ChoiceField(choices=[
        ('delete', '删除'),
        ('enable', '启用'),
        ('disable', '禁用'),
        ('move_group', '移动分组'),
        ('add_tags', '添加标签'),
        ('remove_tags', '移除标签')
    ])
    
    # 可选参数
    target_group_id = serializers.IntegerField(required=False)
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False
    )
    
    def validate_device_ids(self, value):
        """验证设备ID列表"""
        existing_ids = set(Device.objects.filter(id__in=value).values_list('id', flat=True))
        invalid_ids = set(value) - existing_ids
        if invalid_ids:
            raise serializers.ValidationError(f"以下设备ID不存在: {list(invalid_ids)}")
        return value
    
    def validate(self, attrs):
        """验证批量操作参数"""
        operation = attrs.get('operation')
        
        if operation == 'move_group':
            if not attrs.get('target_group_id'):
                raise serializers.ValidationError("移动分组操作需要指定目标分组ID")
            
            try:
                DeviceGroup.objects.get(id=attrs['target_group_id'])
            except DeviceGroup.DoesNotExist:
                raise serializers.ValidationError("目标分组不存在")
        
        elif operation in ['add_tags', 'remove_tags']:
            if not attrs.get('tags'):
                raise serializers.ValidationError("标签操作需要指定标签列表")
        
        return attrs


class DeviceStatsSerializer(serializers.Serializer):
    """设备统计序列化器"""
    total_devices = serializers.IntegerField()
    online_devices = serializers.IntegerField()
    offline_devices = serializers.IntegerField()
    unknown_devices = serializers.IntegerField()
    protocol_stats = serializers.DictField()
    group_stats = serializers.DictField()
    status_trend = serializers.ListField()


class DeviceExportSerializer(serializers.Serializer):
    """设备导出序列化器"""
    format = serializers.ChoiceField(choices=[
        ('csv', 'CSV'),
        ('excel', 'Excel'),
        ('json', 'JSON')
    ], default='csv')
    
    fields = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="要导出的字段列表，为空则导出所有字段"
    )
    
    group_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="要导出的设备分组ID列表"
    )
    
    protocols = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="要导出的协议类型列表"
    )
    
    status = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="要导出的设备状态列表"
    )


class DeviceImportSerializer(serializers.Serializer):
    """设备导入序列化器"""
    file = serializers.FileField(
        help_text="支持CSV、Excel格式的设备信息文件"
    )
    
    update_existing = serializers.BooleanField(
        default=False,
        help_text="是否更新已存在的设备（基于IP地址匹配）"
    )
    
    default_group_id = serializers.IntegerField(
        required=False,
        help_text="默认设备分组ID"
    )
    
    def validate_file(self, value):
        """验证上传文件"""
        if not value.name.endswith(('.csv', '.xlsx', '.xls')):
            raise serializers.ValidationError("只支持CSV和Excel格式文件")
        
        if value.size > 10 * 1024 * 1024:  # 10MB
            raise serializers.ValidationError("文件大小不能超过10MB")
        
        return value
    
    def validate_default_group_id(self, value):
        """验证默认分组"""
        if value:
            try:
                DeviceGroup.objects.get(id=value)
            except DeviceGroup.DoesNotExist:
                raise serializers.ValidationError("默认分组不存在")
        return value