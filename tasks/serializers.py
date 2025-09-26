from rest_framework import serializers
from django.utils import timezone
from datetime import datetime
import json
from .models import TaskTemplate, CollectionTask, TaskExecution
from devices.models import Device, DeviceGroup
from collectors.models import Collector


class TaskTemplateSerializer(serializers.ModelSerializer):
    """任务模板序列化器"""
    
    class Meta:
        model = TaskTemplate
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def validate_config(self, value):
        """验证配置格式"""
        if isinstance(value, str):
            try:
                json.loads(value)
            except json.JSONDecodeError:
                raise serializers.ValidationError("配置必须是有效的JSON格式")
        return value
    
    def validate_cron_expression(self, value):
        """验证CRON表达式格式"""
        if value:
            # 简单的CRON表达式验证
            parts = value.split()
            if len(parts) != 5:
                raise serializers.ValidationError("CRON表达式必须包含5个部分")
        return value


class CollectionTaskSerializer(serializers.ModelSerializer):
    """采集任务序列化器"""
    template_name = serializers.CharField(source='template.name', read_only=True)
    target_device_names = serializers.SerializerMethodField()
    target_group_names = serializers.SerializerMethodField()
    collector_name = serializers.CharField(source='collector.name', read_only=True)
    next_run_time_display = serializers.SerializerMethodField()
    
    class Meta:
        model = CollectionTask
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at', 'last_run_time', 'next_run_time')
    
    def get_target_device_names(self, obj):
        """获取目标设备名称列表"""
        return [device.name for device in obj.target_devices.all()]
    
    def get_target_group_names(self, obj):
        """获取目标设备组名称列表"""
        return [group.name for group in obj.target_groups.all()]
    
    def get_next_run_time_display(self, obj):
        """获取下次运行时间显示"""
        if obj.next_run_time:
            return obj.next_run_time.strftime('%Y-%m-%d %H:%M:%S')
        return None
    
    def validate_cron_expression(self, value):
        """验证CRON表达式格式"""
        if value:
            parts = value.split()
            if len(parts) != 5:
                raise serializers.ValidationError("CRON表达式必须包含5个部分")
        return value
    
    def validate(self, data):
        """验证任务数据"""
        # 检查是否至少指定了一个目标（设备或设备组）
        target_devices = data.get('target_devices', [])
        target_groups = data.get('target_groups', [])
        
        if not target_devices and not target_groups:
            raise serializers.ValidationError("必须至少指定一个目标设备或设备组")
        
        # 检查调度配置
        schedule_type = data.get('schedule_type')
        if schedule_type == 'cron' and not data.get('cron_expression'):
            raise serializers.ValidationError("CRON调度类型必须提供CRON表达式")
        elif schedule_type == 'interval' and not data.get('interval_seconds'):
            raise serializers.ValidationError("间隔调度类型必须提供间隔秒数")
        
        return data


class CollectionTaskCreateSerializer(serializers.ModelSerializer):
    """采集任务创建序列化器"""
    
    class Meta:
        model = CollectionTask
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at', 'last_run_time', 'next_run_time')
    
    def validate_cron_expression(self, value):
        """验证CRON表达式格式"""
        if value:
            parts = value.split()
            if len(parts) != 5:
                raise serializers.ValidationError("CRON表达式必须包含5个部分")
        return value
    
    def validate(self, data):
        """验证任务数据"""
        # 检查是否至少指定了一个目标（设备或设备组）
        target_devices = data.get('target_devices', [])
        target_groups = data.get('target_groups', [])
        
        if not target_devices and not target_groups:
            raise serializers.ValidationError("必须至少指定一个目标设备或设备组")
        
        # 检查调度配置
        schedule_type = data.get('schedule_type')
        if schedule_type == 'cron' and not data.get('cron_expression'):
            raise serializers.ValidationError("CRON调度类型必须提供CRON表达式")
        elif schedule_type == 'interval' and not data.get('interval_seconds'):
            raise serializers.ValidationError("间隔调度类型必须提供间隔秒数")
        
        return data


class CollectionTaskUpdateSerializer(serializers.ModelSerializer):
    """采集任务更新序列化器"""
    
    class Meta:
        model = CollectionTask
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def validate_cron_expression(self, value):
        """验证CRON表达式格式"""
        if value:
            parts = value.split()
            if len(parts) != 5:
                raise serializers.ValidationError("CRON表达式必须包含5个部分")
        return value


class TaskExecutionSerializer(serializers.ModelSerializer):
    """任务执行记录序列化器"""
    task_name = serializers.CharField(source='task.name', read_only=True)
    collector_name = serializers.CharField(source='collector.name', read_only=True)
    duration_display = serializers.SerializerMethodField()
    
    class Meta:
        model = TaskExecution
        fields = '__all__'
        read_only_fields = ('id', 'created_at')
    
    def get_duration_display(self, obj):
        """获取执行时长显示"""
        if obj.start_time and obj.end_time:
            duration = obj.end_time - obj.start_time
            return str(duration)
        return None


class TaskBatchOperationSerializer(serializers.Serializer):
    """任务批量操作序列化器"""
    task_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        help_text="任务ID列表"
    )
    operation = serializers.ChoiceField(
        choices=['start', 'stop', 'delete', 'enable', 'disable'],
        help_text="操作类型"
    )


class TaskStatsSerializer(serializers.Serializer):
    """任务统计序列化器"""
    total_tasks = serializers.IntegerField()
    active_tasks = serializers.IntegerField()
    paused_tasks = serializers.IntegerField()
    completed_tasks = serializers.IntegerField()
    failed_tasks = serializers.IntegerField()
    
    # 按状态统计
    status_stats = serializers.DictField()
    
    # 按类型统计
    type_stats = serializers.DictField()
    
    # 按优先级统计
    priority_stats = serializers.DictField()
    
    # 执行趋势（最近7天）
    execution_trend = serializers.ListField()
    
    # 成功率趋势
    success_rate_trend = serializers.ListField()


class TaskExportSerializer(serializers.Serializer):
    """任务导出序列化器"""
    format = serializers.ChoiceField(
        choices=['csv', 'json'],
        default='csv',
        help_text="导出格式"
    )
    fields = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="导出字段列表"
    )
    template_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="模板ID列表"
    )
    collector_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="采集器ID列表"
    )
    status = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="状态列表"
    )
    priority = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="优先级列表"
    )


class TaskImportSerializer(serializers.Serializer):
    """任务导入序列化器"""
    file = serializers.FileField(help_text="导入文件（CSV或Excel）")
    update_existing = serializers.BooleanField(
        default=False,
        help_text="是否更新已存在的任务"
    )
    default_template_id = serializers.IntegerField(
        required=False,
        help_text="默认模板ID"
    )
    default_collector_id = serializers.IntegerField(
        required=False,
        help_text="默认采集器ID"
    )
    
    def validate_file(self, value):
        """验证文件格式"""
        if not value.name.endswith(('.csv', '.xlsx', '.xls')):
            raise serializers.ValidationError("只支持CSV和Excel文件格式")
        return value


class TaskScheduleSerializer(serializers.Serializer):
    """任务调度序列化器"""
    task_id = serializers.IntegerField(help_text="任务ID")
    action = serializers.ChoiceField(
        choices=['start', 'stop', 'pause', 'resume'],
        help_text="调度操作"
    )
    schedule_time = serializers.DateTimeField(
        required=False,
        help_text="调度时间（可选）"
    )


class TaskLogSerializer(serializers.Serializer):
    """任务日志序列化器"""
    task_id = serializers.IntegerField()
    level = serializers.ChoiceField(
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO'
    )
    message = serializers.CharField(max_length=1000)
    timestamp = serializers.DateTimeField(default=timezone.now)
    metadata = serializers.JSONField(required=False)