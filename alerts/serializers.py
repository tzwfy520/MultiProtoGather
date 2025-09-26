from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import AlertRule, Alert, NotificationChannel, NotificationLog
from devices.models import Device, DeviceGroup
from tasks.models import CollectionTask
from results.models import CollectionResult
import json
import re

User = get_user_model()


class AlertRuleSerializer(serializers.ModelSerializer):
    """告警规则序列化器"""
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    device_names = serializers.SerializerMethodField()
    task_names = serializers.SerializerMethodField()
    device_group_names = serializers.SerializerMethodField()
    
    class Meta:
        model = AlertRule
        fields = [
            'id', 'name', 'description', 'rule_type', 'severity',
            'tasks', 'devices', 'device_groups', 'conditions',
            'threshold_value', 'operator', 'pattern', 'enabled',
            'check_interval', 'consecutive_count', 'recovery_condition',
            'suppression_duration', 'max_alerts_per_hour',
            'created_by', 'created_by_name', 'created_at', 'updated_at',
            'device_names', 'task_names', 'device_group_names'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']
    
    def get_device_names(self, obj):
        """获取关联设备名称"""
        return [device.name for device in obj.devices.all()]
    
    def get_task_names(self, obj):
        """获取关联任务名称"""
        return [task.name for task in obj.tasks.all()]
    
    def get_device_group_names(self, obj):
        """获取设备组名称"""
        if not obj.device_groups:
            return []
        try:
            group_ids = obj.device_groups if isinstance(obj.device_groups, list) else []
            groups = DeviceGroup.objects.filter(id__in=group_ids)
            return [group.name for group in groups]
        except:
            return []
    
    def validate_conditions(self, value):
        """验证告警条件"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("告警条件必须是字典格式")
        return value
    
    def validate_recovery_condition(self, value):
        """验证恢复条件"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("恢复条件必须是字典格式")
        return value
    
    def validate_pattern(self, value):
        """验证正则表达式模式"""
        if value:
            try:
                re.compile(value)
            except re.error:
                raise serializers.ValidationError("无效的正则表达式")
        return value
    
    def validate(self, attrs):
        """整体验证"""
        rule_type = attrs.get('rule_type')
        
        # 阈值告警需要阈值和操作符
        if rule_type == 'threshold':
            if not attrs.get('threshold_value') and attrs.get('threshold_value') != 0:
                raise serializers.ValidationError("阈值告警必须设置阈值")
            if not attrs.get('operator'):
                raise serializers.ValidationError("阈值告警必须设置比较操作符")
        
        # 模式匹配需要模式
        elif rule_type == 'pattern':
            if not attrs.get('pattern'):
                raise serializers.ValidationError("模式匹配告警必须设置匹配模式")
        
        # 检查间隔不能小于60秒
        if attrs.get('check_interval', 0) < 60:
            raise serializers.ValidationError("检查间隔不能小于60秒")
        
        return attrs


class AlertRuleCreateSerializer(AlertRuleSerializer):
    """告警规则创建序列化器"""
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class AlertRuleUpdateSerializer(AlertRuleSerializer):
    """告警规则更新序列化器"""
    pass


class AlertSerializer(serializers.ModelSerializer):
    """告警记录序列化器"""
    rule_name = serializers.CharField(source='rule.name', read_only=True)
    task_name = serializers.CharField(source='task.name', read_only=True)
    device_name = serializers.CharField(source='device.name', read_only=True)
    device_ip = serializers.CharField(source='device.ip_address', read_only=True)
    acknowledged_by_name = serializers.CharField(source='acknowledged_by.username', read_only=True)
    resolved_by_name = serializers.CharField(source='resolved_by.username', read_only=True)
    duration_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Alert
        fields = [
            'id', 'rule', 'rule_name', 'task', 'task_name',
            'device', 'device_name', 'device_ip', 'result',
            'title', 'message', 'severity', 'status',
            'trigger_data', 'context_data',
            'first_occurred_at', 'last_occurred_at',
            'acknowledged_at', 'resolved_at',
            'acknowledged_by', 'acknowledged_by_name',
            'resolved_by', 'resolved_by_name',
            'occurrence_count', 'notification_count',
            'created_at', 'updated_at', 'duration_display'
        ]
        read_only_fields = [
            'rule', 'task', 'device', 'result', 'title', 'message',
            'severity', 'trigger_data', 'context_data',
            'first_occurred_at', 'last_occurred_at', 'occurrence_count',
            'notification_count', 'created_at', 'updated_at'
        ]
    
    def get_duration_display(self, obj):
        """获取持续时间显示"""
        if obj.duration:
            total_seconds = int(obj.duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            
            if hours > 0:
                return f"{hours}小时{minutes}分钟"
            elif minutes > 0:
                return f"{minutes}分钟{seconds}秒"
            else:
                return f"{seconds}秒"
        return None


class AlertAcknowledgeSerializer(serializers.Serializer):
    """告警确认序列化器"""
    alert_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        help_text="要确认的告警ID列表"
    )
    comment = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="确认备注"
    )


class AlertResolveSerializer(serializers.Serializer):
    """告警解决序列化器"""
    alert_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        help_text="要解决的告警ID列表"
    )
    comment = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="解决备注"
    )


class NotificationChannelSerializer(serializers.ModelSerializer):
    """通知渠道序列化器"""
    
    class Meta:
        model = NotificationChannel
        fields = [
            'id', 'name', 'description', 'channel_type', 'config',
            'enabled', 'rate_limit', 'retry_count', 'timeout',
            'severity_filter', 'time_filter',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def validate_config(self, value):
        """验证渠道配置"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("渠道配置必须是字典格式")
        
        channel_type = self.initial_data.get('channel_type')
        
        # 根据渠道类型验证必需的配置项
        if channel_type == 'email':
            required_fields = ['smtp_host', 'smtp_port', 'username', 'password']
        elif channel_type == 'dingtalk':
            required_fields = ['webhook_url']
        elif channel_type == 'wechat':
            required_fields = ['corp_id', 'corp_secret', 'agent_id']
        elif channel_type == 'sms':
            required_fields = ['api_key', 'api_secret']
        elif channel_type == 'webhook':
            required_fields = ['url']
        elif channel_type == 'slack':
            required_fields = ['webhook_url']
        else:
            required_fields = []
        
        for field in required_fields:
            if field not in value or not value[field]:
                raise serializers.ValidationError(f"缺少必需的配置项: {field}")
        
        return value
    
    def validate_severity_filter(self, value):
        """验证级别过滤"""
        if not isinstance(value, list):
            raise serializers.ValidationError("级别过滤必须是列表格式")
        
        valid_severities = ['critical', 'high', 'medium', 'low', 'info']
        for severity in value:
            if severity not in valid_severities:
                raise serializers.ValidationError(f"无效的告警级别: {severity}")
        
        return value
    
    def validate_time_filter(self, value):
        """验证时间过滤"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("时间过滤必须是字典格式")
        return value


class NotificationLogSerializer(serializers.ModelSerializer):
    """通知日志序列化器"""
    alert_title = serializers.CharField(source='alert.title', read_only=True)
    channel_name = serializers.CharField(source='channel.name', read_only=True)
    channel_type = serializers.CharField(source='channel.channel_type', read_only=True)
    
    class Meta:
        model = NotificationLog
        fields = [
            'id', 'alert', 'alert_title', 'channel', 'channel_name',
            'channel_type', 'status', 'recipients', 'subject',
            'content', 'response_data', 'error_message',
            'retry_count', 'sent_at', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'alert', 'channel', 'status', 'recipients', 'subject',
            'content', 'response_data', 'error_message', 'retry_count',
            'sent_at', 'created_at', 'updated_at'
        ]


class AlertStatsSerializer(serializers.Serializer):
    """告警统计序列化器"""
    total_alerts = serializers.IntegerField()
    active_alerts = serializers.IntegerField()
    acknowledged_alerts = serializers.IntegerField()
    resolved_alerts = serializers.IntegerField()
    suppressed_alerts = serializers.IntegerField()
    
    # 按级别统计
    critical_alerts = serializers.IntegerField()
    high_alerts = serializers.IntegerField()
    medium_alerts = serializers.IntegerField()
    low_alerts = serializers.IntegerField()
    info_alerts = serializers.IntegerField()
    
    # 按规则类型统计
    threshold_alerts = serializers.IntegerField()
    pattern_alerts = serializers.IntegerField()
    anomaly_alerts = serializers.IntegerField()
    status_alerts = serializers.IntegerField()
    timeout_alerts = serializers.IntegerField()
    
    # 7天趋势
    daily_trends = serializers.ListField(
        child=serializers.DictField(),
        help_text="7天告警趋势"
    )


class AlertBatchOperationSerializer(serializers.Serializer):
    """告警批量操作序列化器"""
    OPERATION_CHOICES = [
        ('acknowledge', '确认'),
        ('resolve', '解决'),
        ('delete', '删除'),
    ]
    
    operation = serializers.ChoiceField(
        choices=OPERATION_CHOICES,
        help_text="操作类型"
    )
    alert_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        help_text="告警ID列表"
    )
    comment = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="操作备注"
    )


class AlertExportSerializer(serializers.Serializer):
    """告警导出序列化器"""
    FORMAT_CHOICES = [
        ('csv', 'CSV'),
        ('json', 'JSON'),
    ]
    
    format = serializers.ChoiceField(
        choices=FORMAT_CHOICES,
        default='csv',
        help_text="导出格式"
    )
    
    # 过滤条件
    rule_id = serializers.IntegerField(required=False, help_text="告警规则ID")
    severity = serializers.CharField(required=False, help_text="告警级别")
    status = serializers.CharField(required=False, help_text="告警状态")
    device_id = serializers.IntegerField(required=False, help_text="设备ID")
    task_id = serializers.IntegerField(required=False, help_text="任务ID")
    start_time = serializers.DateTimeField(required=False, help_text="开始时间")
    end_time = serializers.DateTimeField(required=False, help_text="结束时间")
    
    def validate(self, attrs):
        start_time = attrs.get('start_time')
        end_time = attrs.get('end_time')
        
        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError("开始时间必须早于结束时间")
        
        return attrs