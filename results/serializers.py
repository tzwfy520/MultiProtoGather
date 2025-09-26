from rest_framework import serializers
from django.utils import timezone
from datetime import datetime, timedelta
import json

from .models import CollectionResult, ResultAnalysis, DataExport
from devices.models import Device
from tasks.models import CollectionTask, TaskExecution


class CollectionResultSerializer(serializers.ModelSerializer):
    """采集结果序列化器"""
    task_name = serializers.CharField(source='task.name', read_only=True)
    device_name = serializers.CharField(source='device.name', read_only=True)
    device_ip = serializers.CharField(source='device.ip_address', read_only=True)
    execution_duration = serializers.SerializerMethodField()
    data_size_mb = serializers.SerializerMethodField()
    
    class Meta:
        model = CollectionResult
        fields = [
            'id', 'task_execution', 'task', 'device', 'task_name', 'device_name', 'device_ip',
            'status', 'data_type', 'raw_data', 'parsed_data', 'data_size', 'data_size_mb',
            'checksum', 'encoding', 'record_count', 'error_count', 'warning_count',
            'processed', 'processed_at', 'processor', 'file_path', 'archived', 'archive_path',
            'execution_duration', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_execution_duration(self, obj):
        """获取执行时长"""
        if obj.task_execution:
            return obj.task_execution.duration
        return None
    
    def get_data_size_mb(self, obj):
        """获取数据大小(MB)"""
        if obj.data_size:
            return round(obj.data_size / (1024 * 1024), 2)
        return 0


class CollectionResultCreateSerializer(serializers.ModelSerializer):
    """采集结果创建序列化器"""
    
    class Meta:
        model = CollectionResult
        fields = [
            'task_execution', 'task', 'device', 'status', 'data_type', 'raw_data',
            'parsed_data', 'data_size', 'checksum', 'encoding', 'record_count',
            'error_count', 'warning_count', 'file_path'
        ]
    
    def validate(self, attrs):
        # 验证任务执行记录与任务、设备的一致性
        task_execution = attrs.get('task_execution')
        task = attrs.get('task')
        device = attrs.get('device')
        
        if task_execution and task and task_execution.task != task:
            raise serializers.ValidationError("任务执行记录与指定任务不匹配")
        
        if task_execution and device and task_execution.device != device:
            raise serializers.ValidationError("任务执行记录与指定设备不匹配")
        
        # 验证JSON数据格式
        if attrs.get('data_type') == 'json' and attrs.get('raw_data'):
            try:
                json.loads(attrs['raw_data'])
            except json.JSONDecodeError:
                raise serializers.ValidationError("原始数据不是有效的JSON格式")
        
        return attrs


class CollectionResultUpdateSerializer(serializers.ModelSerializer):
    """采集结果更新序列化器"""
    
    class Meta:
        model = CollectionResult
        fields = [
            'status', 'parsed_data', 'record_count', 'error_count', 'warning_count',
            'processed', 'processed_at', 'processor', 'archived', 'archive_path'
        ]


class ResultAnalysisSerializer(serializers.ModelSerializer):
    """结果分析序列化器"""
    task_name = serializers.CharField(source='task.name', read_only=True)
    device_names = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    duration_days = serializers.SerializerMethodField()
    
    class Meta:
        model = ResultAnalysis
        fields = [
            'id', 'name', 'description', 'analysis_type', 'task', 'task_name',
            'devices', 'device_names', 'time_range_start', 'time_range_end', 'duration_days',
            'analysis_config', 'filters', 'result_data', 'summary', 'insights',
            'status', 'progress', 'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']
    
    def get_device_names(self, obj):
        """获取设备名称列表"""
        return [device.name for device in obj.devices.all()]
    
    def get_duration_days(self, obj):
        """获取分析时间范围天数"""
        if obj.time_range_start and obj.time_range_end:
            delta = obj.time_range_end - obj.time_range_start
            return delta.days
        return 0


class ResultAnalysisCreateSerializer(serializers.ModelSerializer):
    """结果分析创建序列化器"""
    
    class Meta:
        model = ResultAnalysis
        fields = [
            'name', 'description', 'analysis_type', 'task', 'devices',
            'time_range_start', 'time_range_end', 'analysis_config', 'filters'
        ]
    
    def validate(self, attrs):
        # 验证时间范围
        start_time = attrs.get('time_range_start')
        end_time = attrs.get('time_range_end')
        
        if start_time and end_time:
            if start_time >= end_time:
                raise serializers.ValidationError("开始时间必须早于结束时间")
            
            # 限制分析时间范围不超过1年
            if (end_time - start_time).days > 365:
                raise serializers.ValidationError("分析时间范围不能超过1年")
        
        # 验证分析配置
        analysis_config = attrs.get('analysis_config', {})
        analysis_type = attrs.get('analysis_type')
        
        if analysis_type == 'trend' and not analysis_config.get('metrics'):
            raise serializers.ValidationError("趋势分析需要指定分析指标")
        
        if analysis_type == 'comparison' and not analysis_config.get('compare_fields'):
            raise serializers.ValidationError("对比分析需要指定对比字段")
        
        return attrs


class ResultAnalysisUpdateSerializer(serializers.ModelSerializer):
    """结果分析更新序列化器"""
    
    class Meta:
        model = ResultAnalysis
        fields = [
            'name', 'description', 'analysis_config', 'filters',
            'result_data', 'summary', 'insights', 'status', 'progress'
        ]


class DataExportSerializer(serializers.ModelSerializer):
    """数据导出序列化器"""
    task_name = serializers.CharField(source='task.name', read_only=True)
    device_names = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    file_size_mb = serializers.SerializerMethodField()
    is_expired = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = DataExport
        fields = [
            'id', 'name', 'description', 'export_format', 'task', 'task_name',
            'devices', 'device_names', 'time_range_start', 'time_range_end',
            'export_config', 'filters', 'columns', 'status', 'file_path',
            'file_size', 'file_size_mb', 'record_count', 'download_count',
            'last_download_at', 'expires_at', 'is_expired', 'created_by',
            'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']
    
    def get_device_names(self, obj):
        """获取设备名称列表"""
        return [device.name for device in obj.devices.all()]
    
    def get_file_size_mb(self, obj):
        """获取文件大小(MB)"""
        if obj.file_size:
            return round(obj.file_size / (1024 * 1024), 2)
        return 0


class DataExportCreateSerializer(serializers.ModelSerializer):
    """数据导出创建序列化器"""
    
    class Meta:
        model = DataExport
        fields = [
            'name', 'description', 'export_format', 'task', 'devices',
            'time_range_start', 'time_range_end', 'export_config', 'filters', 'columns'
        ]
    
    def validate(self, attrs):
        # 验证时间范围
        start_time = attrs.get('time_range_start')
        end_time = attrs.get('time_range_end')
        
        if start_time and end_time:
            if start_time >= end_time:
                raise serializers.ValidationError("开始时间必须早于结束时间")
            
            # 限制导出时间范围不超过6个月
            if (end_time - start_time).days > 180:
                raise serializers.ValidationError("导出时间范围不能超过6个月")
        
        # 验证导出格式配置
        export_format = attrs.get('export_format')
        export_config = attrs.get('export_config', {})
        
        if export_format == 'excel' and export_config.get('max_rows', 0) > 1000000:
            raise serializers.ValidationError("Excel格式导出行数不能超过100万")
        
        if export_format == 'pdf' and not export_config.get('template'):
            raise serializers.ValidationError("PDF导出需要指定模板")
        
        # 验证导出列
        columns = attrs.get('columns', [])
        if not columns:
            raise serializers.ValidationError("必须指定至少一个导出列")
        
        return attrs


class DataExportUpdateSerializer(serializers.ModelSerializer):
    """数据导出更新序列化器"""
    
    class Meta:
        model = DataExport
        fields = [
            'name', 'description', 'export_config', 'filters', 'columns',
            'status', 'file_path', 'file_size', 'record_count', 'expires_at'
        ]


class ResultStatsSerializer(serializers.Serializer):
    """结果统计序列化器"""
    # 基础统计
    total_results = serializers.IntegerField()
    success_results = serializers.IntegerField()
    failed_results = serializers.IntegerField()
    partial_results = serializers.IntegerField()
    timeout_results = serializers.IntegerField()
    error_results = serializers.IntegerField()
    
    # 数据类型统计
    text_results = serializers.IntegerField()
    json_results = serializers.IntegerField()
    xml_results = serializers.IntegerField()
    csv_results = serializers.IntegerField()
    binary_results = serializers.IntegerField()
    
    # 处理状态统计
    processed_results = serializers.IntegerField()
    unprocessed_results = serializers.IntegerField()
    archived_results = serializers.IntegerField()
    
    # 分析统计
    total_analysis = serializers.IntegerField()
    pending_analysis = serializers.IntegerField()
    running_analysis = serializers.IntegerField()
    completed_analysis = serializers.IntegerField()
    failed_analysis = serializers.IntegerField()
    
    # 导出统计
    total_exports = serializers.IntegerField()
    pending_exports = serializers.IntegerField()
    processing_exports = serializers.IntegerField()
    completed_exports = serializers.IntegerField()
    failed_exports = serializers.IntegerField()
    
    # 趋势数据
    daily_trends = serializers.ListField(
        child=serializers.DictField()
    )


class ResultBatchOperationSerializer(serializers.Serializer):
    """结果批量操作序列化器"""
    OPERATION_CHOICES = [
        ('process', '处理'),
        ('archive', '归档'),
        ('delete', '删除'),
        ('export', '导出'),
    ]
    
    operation = serializers.ChoiceField(choices=OPERATION_CHOICES)
    result_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=1000
    )
    options = serializers.DictField(required=False)
    
    def validate_result_ids(self, value):
        """验证结果ID列表"""
        # 检查结果是否存在
        existing_ids = CollectionResult.objects.filter(id__in=value).values_list('id', flat=True)
        missing_ids = set(value) - set(existing_ids)
        
        if missing_ids:
            raise serializers.ValidationError(f"以下结果ID不存在: {list(missing_ids)}")
        
        return value


class ResultExportSerializer(serializers.Serializer):
    """结果导出序列化器"""
    FORMAT_CHOICES = [
        ('csv', 'CSV'),
        ('json', 'JSON'),
        ('excel', 'Excel'),
    ]
    
    format = serializers.ChoiceField(choices=FORMAT_CHOICES, default='csv')
    task_id = serializers.IntegerField(required=False)
    device_id = serializers.IntegerField(required=False)
    status = serializers.CharField(required=False)
    data_type = serializers.CharField(required=False)
    start_time = serializers.DateTimeField(required=False)
    end_time = serializers.DateTimeField(required=False)
    include_raw_data = serializers.BooleanField(default=False)
    include_parsed_data = serializers.BooleanField(default=True)
    
    def validate(self, attrs):
        # 验证时间范围
        start_time = attrs.get('start_time')
        end_time = attrs.get('end_time')
        
        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError("开始时间必须早于结束时间")
        
        return attrs


class ResultSearchSerializer(serializers.Serializer):
    """结果搜索序列化器"""
    query = serializers.CharField(required=False)
    task_id = serializers.IntegerField(required=False)
    device_id = serializers.IntegerField(required=False)
    status = serializers.CharField(required=False)
    data_type = serializers.CharField(required=False)
    start_time = serializers.DateTimeField(required=False)
    end_time = serializers.DateTimeField(required=False)
    processed = serializers.BooleanField(required=False)
    archived = serializers.BooleanField(required=False)
    
    # 排序选项
    ordering = serializers.CharField(required=False, default='-created_at')
    
    # 分页选项
    page = serializers.IntegerField(required=False, default=1, min_value=1)
    page_size = serializers.IntegerField(required=False, default=20, min_value=1, max_value=100)