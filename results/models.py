from django.db import models
from django.contrib.auth import get_user_model
from devices.models import Device
from tasks.models import CollectionTask, TaskExecution
import json

User = get_user_model()


class CollectionResult(models.Model):
    """采集结果模型"""
    RESULT_STATUS = [
        ('success', '成功'),
        ('partial', '部分成功'),
        ('failed', '失败'),
        ('timeout', '超时'),
        ('error', '错误'),
    ]

    DATA_TYPE = [
        ('text', '文本'),
        ('json', 'JSON'),
        ('xml', 'XML'),
        ('csv', 'CSV'),
        ('binary', '二进制'),
    ]

    task_execution = models.OneToOneField(
        TaskExecution, 
        on_delete=models.CASCADE, 
        verbose_name="任务执行记录"
    )
    task = models.ForeignKey(
        CollectionTask, 
        on_delete=models.CASCADE, 
        verbose_name="采集任务"
    )
    device = models.ForeignKey(
        Device, 
        on_delete=models.CASCADE, 
        verbose_name="目标设备"
    )
    
    # 结果信息
    status = models.CharField(
        max_length=20, 
        choices=RESULT_STATUS, 
        verbose_name="结果状态"
    )
    data_type = models.CharField(
        max_length=20, 
        choices=DATA_TYPE, 
        default='text', 
        verbose_name="数据类型"
    )
    raw_data = models.TextField(verbose_name="原始数据")
    parsed_data = models.JSONField(null=True, blank=True, verbose_name="解析后数据")
    
    # 元数据
    data_size = models.IntegerField(default=0, verbose_name="数据大小(字节)")
    checksum = models.CharField(max_length=64, blank=True, verbose_name="数据校验和")
    encoding = models.CharField(max_length=20, default='utf-8', verbose_name="编码格式")
    
    # 统计信息
    record_count = models.IntegerField(null=True, blank=True, verbose_name="记录数量")
    error_count = models.IntegerField(default=0, verbose_name="错误数量")
    warning_count = models.IntegerField(default=0, verbose_name="警告数量")
    
    # 处理信息
    processed = models.BooleanField(default=False, verbose_name="是否已处理")
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name="处理时间")
    processor = models.CharField(max_length=100, blank=True, verbose_name="处理器")
    
    # 存储信息
    file_path = models.CharField(max_length=500, blank=True, verbose_name="文件路径")
    archived = models.BooleanField(default=False, verbose_name="是否已归档")
    archive_path = models.CharField(max_length=500, blank=True, verbose_name="归档路径")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = 'collection_results'
        verbose_name = "采集结果"
        verbose_name_plural = "采集结果"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.task.name} - {self.device.name} - {self.status}"

    def get_parsed_data(self):
        """获取解析后的数据"""
        if self.parsed_data:
            return self.parsed_data
        
        # 如果没有解析数据，尝试解析原始数据
        if self.data_type == 'json':
            try:
                return json.loads(self.raw_data)
            except json.JSONDecodeError:
                return None
        
        return self.raw_data

    def calculate_checksum(self):
        """计算数据校验和"""
        import hashlib
        return hashlib.sha256(self.raw_data.encode()).hexdigest()


class ResultAnalysis(models.Model):
    """结果分析模型"""
    ANALYSIS_TYPE = [
        ('trend', '趋势分析'),
        ('comparison', '对比分析'),
        ('anomaly', '异常检测'),
        ('statistics', '统计分析'),
        ('pattern', '模式识别'),
    ]

    name = models.CharField(max_length=100, verbose_name="分析名称")
    description = models.TextField(blank=True, verbose_name="分析描述")
    analysis_type = models.CharField(
        max_length=20, 
        choices=ANALYSIS_TYPE, 
        verbose_name="分析类型"
    )
    
    # 分析范围
    task = models.ForeignKey(
        CollectionTask, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        verbose_name="关联任务"
    )
    devices = models.ManyToManyField(
        Device, 
        blank=True, 
        verbose_name="分析设备"
    )
    time_range_start = models.DateTimeField(verbose_name="开始时间")
    time_range_end = models.DateTimeField(verbose_name="结束时间")
    
    # 分析配置
    analysis_config = models.JSONField(default=dict, verbose_name="分析配置")
    filters = models.JSONField(default=dict, verbose_name="过滤条件")
    
    # 分析结果
    result_data = models.JSONField(null=True, blank=True, verbose_name="分析结果")
    summary = models.TextField(blank=True, verbose_name="结果摘要")
    insights = models.JSONField(default=list, verbose_name="洞察发现")
    
    # 状态信息
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', '待分析'),
            ('running', '分析中'),
            ('completed', '已完成'),
            ('failed', '失败'),
        ],
        default='pending',
        verbose_name="分析状态"
    )
    progress = models.IntegerField(default=0, verbose_name="进度百分比")
    
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name="创建者"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = 'result_analysis'
        verbose_name = "结果分析"
        verbose_name_plural = "结果分析"
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class DataExport(models.Model):
    """数据导出模型"""
    EXPORT_FORMAT = [
        ('csv', 'CSV'),
        ('excel', 'Excel'),
        ('json', 'JSON'),
        ('xml', 'XML'),
        ('pdf', 'PDF'),
    ]

    EXPORT_STATUS = [
        ('pending', '待导出'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]

    name = models.CharField(max_length=100, verbose_name="导出名称")
    description = models.TextField(blank=True, verbose_name="导出描述")
    export_format = models.CharField(
        max_length=20, 
        choices=EXPORT_FORMAT, 
        verbose_name="导出格式"
    )
    
    # 导出范围
    task = models.ForeignKey(
        CollectionTask, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        verbose_name="关联任务"
    )
    devices = models.ManyToManyField(
        Device, 
        blank=True, 
        verbose_name="导出设备"
    )
    time_range_start = models.DateTimeField(verbose_name="开始时间")
    time_range_end = models.DateTimeField(verbose_name="结束时间")
    
    # 导出配置
    export_config = models.JSONField(default=dict, verbose_name="导出配置")
    filters = models.JSONField(default=dict, verbose_name="过滤条件")
    columns = models.JSONField(default=list, verbose_name="导出列")
    
    # 导出结果
    status = models.CharField(
        max_length=20, 
        choices=EXPORT_STATUS, 
        default='pending', 
        verbose_name="导出状态"
    )
    file_path = models.CharField(max_length=500, blank=True, verbose_name="文件路径")
    file_size = models.IntegerField(null=True, blank=True, verbose_name="文件大小(字节)")
    record_count = models.IntegerField(null=True, blank=True, verbose_name="记录数量")
    
    # 下载信息
    download_count = models.IntegerField(default=0, verbose_name="下载次数")
    last_download_at = models.DateTimeField(null=True, blank=True, verbose_name="最后下载时间")
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="过期时间")
    
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name="创建者"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = 'data_exports'
        verbose_name = "数据导出"
        verbose_name_plural = "数据导出"
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def is_expired(self):
        """是否已过期"""
        if not self.expires_at:
            return False
        from django.utils import timezone
        return timezone.now() > self.expires_at
