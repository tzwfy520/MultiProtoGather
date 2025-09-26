from rest_framework import serializers
from django.utils import timezone
from .models import ServiceZone, Collector, CollectorPerformance, CollectorDeployment


class ServiceZoneSerializer(serializers.ModelSerializer):
    """服务区序列化器"""
    collector_count = serializers.SerializerMethodField()
    online_collector_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ServiceZone
        fields = [
            'id', 'name', 'description', 'server_ip', 'ssh_port', 'ssh_username',
            'ssh_password', 'ssh_private_key', 'status', 'last_heartbeat',
            'cpu_usage', 'memory_usage', 'disk_usage', 'network_usage',
            'metadata', 'created_at', 'updated_at',
            'collector_count', 'online_collector_count'
        ]
        extra_kwargs = {
            'ssh_password': {'write_only': True},
            'ssh_private_key': {'write_only': True},
        }
    
    def get_collector_count(self, obj):
        """获取采集器总数"""
        return obj.collectors.count()
    
    def get_online_collector_count(self, obj):
        """获取在线采集器数量"""
        return obj.collectors.filter(status='online').count()


class ServiceZoneCreateSerializer(serializers.ModelSerializer):
    """服务区创建序列化器"""
    
    class Meta:
        model = ServiceZone
        fields = [
            'name', 'description', 'server_ip', 'ssh_port', 'ssh_username',
            'ssh_password', 'ssh_private_key', 'metadata'
        ]
        extra_kwargs = {
            'ssh_password': {'write_only': True},
            'ssh_private_key': {'write_only': True},
        }
    
    def create(self, validated_data):
        """创建服务区"""
        service_zone = ServiceZone(**validated_data)
        
        # 加密敏感信息
        if 'ssh_password' in validated_data:
            service_zone.set_ssh_password(validated_data['ssh_password'])
        if 'ssh_private_key' in validated_data:
            service_zone.set_ssh_private_key(validated_data['ssh_private_key'])
        
        service_zone.save()
        return service_zone


class ServiceZoneUpdateSerializer(serializers.ModelSerializer):
    """服务区更新序列化器"""
    
    class Meta:
        model = ServiceZone
        fields = [
            'name', 'description', 'server_ip', 'ssh_port', 'ssh_username',
            'ssh_password', 'ssh_private_key', 'metadata'
        ]
        extra_kwargs = {
            'ssh_password': {'write_only': True, 'required': False},
            'ssh_private_key': {'write_only': True, 'required': False},
        }
    
    def update(self, instance, validated_data):
        """更新服务区"""
        # 处理敏感信息
        if 'ssh_password' in validated_data:
            instance.set_ssh_password(validated_data.pop('ssh_password'))
        if 'ssh_private_key' in validated_data:
            instance.set_ssh_private_key(validated_data.pop('ssh_private_key'))
        
        # 更新其他字段
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance


class CollectorSerializer(serializers.ModelSerializer):
    """采集器序列化器"""
    service_zone_name = serializers.CharField(source='service_zone.name', read_only=True)
    uptime = serializers.SerializerMethodField()
    
    class Meta:
        model = Collector
        fields = [
            'id', 'name', 'collector_type', 'version', 'service_zone',
            'service_zone_name', 'container_id', 'image_name', 'port',
            'status', 'last_heartbeat', 'cpu_usage', 'memory_usage',
            'task_count', 'success_rate', 'avg_response_time',
            'tags', 'metadata', 'created_at', 'updated_at', 'uptime'
        ]
    
    def get_uptime(self, obj):
        """计算运行时间"""
        if obj.last_heartbeat:
            uptime_seconds = (timezone.now() - obj.created_at).total_seconds()
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            return f"{days}天{hours}小时{minutes}分钟"
        return "未知"


class CollectorCreateSerializer(serializers.ModelSerializer):
    """采集器创建序列化器"""
    
    class Meta:
        model = Collector
        fields = [
            'name', 'collector_type', 'version', 'service_zone',
            'container_id', 'image_name', 'port', 'tags', 'metadata'
        ]
    
    def validate_name(self, value):
        """验证采集器名称唯一性"""
        if Collector.objects.filter(name=value).exists():
            raise serializers.ValidationError("采集器名称已存在")
        return value
    
    def validate_port(self, value):
        """验证端口范围"""
        if not (1 <= value <= 65535):
            raise serializers.ValidationError("端口号必须在1-65535之间")
        return value


class CollectorUpdateSerializer(serializers.ModelSerializer):
    """采集器更新序列化器"""
    
    class Meta:
        model = Collector
        fields = [
            'name', 'version', 'service_zone', 'container_id',
            'image_name', 'port', 'tags', 'metadata'
        ]
    
    def validate_name(self, value):
        """验证采集器名称唯一性（排除当前实例）"""
        if Collector.objects.filter(name=value).exclude(id=self.instance.id).exists():
            raise serializers.ValidationError("采集器名称已存在")
        return value


class CollectorPerformanceSerializer(serializers.ModelSerializer):
    """采集器性能序列化器"""
    collector_name = serializers.CharField(source='collector.name', read_only=True)
    
    class Meta:
        model = CollectorPerformance
        fields = [
            'id', 'collector', 'collector_name', 'timestamp',
            'cpu_usage', 'memory_usage', 'disk_usage', 'network_in',
            'network_out', 'task_count', 'success_count', 'error_count',
            'avg_response_time', 'metadata'
        ]


class CollectorDeploymentSerializer(serializers.ModelSerializer):
    """采集器部署序列化器"""
    collector_name = serializers.CharField(source='collector.name', read_only=True)
    service_zone_name = serializers.CharField(source='service_zone.name', read_only=True)
    
    class Meta:
        model = CollectorDeployment
        fields = [
            'id', 'collector', 'collector_name', 'service_zone',
            'service_zone_name', 'deployment_type', 'image_name',
            'container_config', 'status', 'deploy_time', 'error_message',
            'metadata'
        ]


class CollectorDeploymentCreateSerializer(serializers.ModelSerializer):
    """采集器部署创建序列化器"""
    
    class Meta:
        model = CollectorDeployment
        fields = [
            'collector', 'service_zone', 'deployment_type',
            'image_name', 'container_config', 'metadata'
        ]
    
    def validate(self, data):
        """验证部署配置"""
        deployment_type = data.get('deployment_type')
        container_config = data.get('container_config', {})
        
        if deployment_type == 'docker':
            # 验证Docker配置
            required_fields = ['image', 'ports']
            for field in required_fields:
                if field not in container_config:
                    raise serializers.ValidationError(f"Docker部署缺少必需配置: {field}")
        
        return data


class CollectorStatsSerializer(serializers.Serializer):
    """采集器统计序列化器"""
    total_collectors = serializers.IntegerField()
    online_collectors = serializers.IntegerField()
    offline_collectors = serializers.IntegerField()
    busy_collectors = serializers.IntegerField()
    type_stats = serializers.DictField()
    service_zone_stats = serializers.DictField()
    performance_trend = serializers.ListField()


class CollectorHeartbeatSerializer(serializers.Serializer):
    """采集器心跳序列化器"""
    collector_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=['online', 'offline', 'busy'])
    cpu_usage = serializers.FloatField(min_value=0, max_value=100, required=False)
    memory_usage = serializers.FloatField(min_value=0, max_value=100, required=False)
    task_count = serializers.IntegerField(min_value=0, required=False)
    success_rate = serializers.FloatField(min_value=0, max_value=100, required=False)
    avg_response_time = serializers.FloatField(min_value=0, required=False)
    metadata = serializers.JSONField(required=False)


class CollectorBatchOperationSerializer(serializers.Serializer):
    """采集器批量操作序列化器"""
    collector_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        error_messages={'min_length': '至少选择一个采集器'}
    )
    operation = serializers.ChoiceField(
        choices=['start', 'stop', 'restart', 'delete', 'update_tags'],
        error_messages={'invalid_choice': '无效的操作类型'}
    )
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        help_text='标签操作时使用'
    )
    
    def validate(self, data):
        """验证批量操作参数"""
        operation = data.get('operation')
        
        if operation == 'update_tags' and not data.get('tags'):
            raise serializers.ValidationError("标签操作需要提供标签列表")
        
        return data


class ServiceZoneConnectionTestSerializer(serializers.Serializer):
    """服务区连接测试序列化器"""
    service_zone_id = serializers.IntegerField()
    test_type = serializers.ChoiceField(
        choices=['ssh', 'ping', 'all'],
        default='all'
    )


class CollectorLogSerializer(serializers.Serializer):
    """采集器日志序列化器"""
    collector_id = serializers.IntegerField()
    log_type = serializers.ChoiceField(
        choices=['stdout', 'stderr', 'all'],
        default='all'
    )
    lines = serializers.IntegerField(min_value=1, max_value=1000, default=100)
    since = serializers.DateTimeField(required=False)


class CollectorExportSerializer(serializers.Serializer):
    """采集器导出序列化器"""
    format = serializers.ChoiceField(choices=['csv', 'json'], default='csv')
    fields = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text='要导出的字段列表，为空则导出所有字段'
    )
    service_zone_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text='服务区ID列表过滤'
    )
    collector_types = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text='采集器类型过滤'
    )
    status = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text='状态过滤'
    )