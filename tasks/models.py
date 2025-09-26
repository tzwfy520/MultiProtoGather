from django.db import models
from django.contrib.auth import get_user_model
from devices.models import Device, DeviceGroup
from collectors.models import Collector
import json

User = get_user_model()


class TaskTemplate(models.Model):
    """任务模板模型"""
    name = models.CharField(max_length=100, unique=True, verbose_name="模板名称")
    description = models.TextField(blank=True, verbose_name="模板描述")
    protocol = models.CharField(
        max_length=20,
        choices=Device.PROTOCOL_CHOICES,
        verbose_name="协议类型"
    )
    
    # 采集配置
    command_template = models.TextField(verbose_name="命令模板")
    timeout = models.IntegerField(default=30, verbose_name="超时时间(秒)")
    retry_count = models.IntegerField(default=3, verbose_name="重试次数")
    retry_interval = models.IntegerField(default=5, verbose_name="重试间隔(秒)")
    
    # 调度配置
    cron_expression = models.CharField(max_length=100, blank=True, verbose_name="CRON表达式")
    schedule_type = models.CharField(
        max_length=20,
        choices=[
            ('once', '单次执行'),
            ('interval', '间隔执行'),
            ('cron', 'CRON表达式'),
            ('manual', '手动执行'),
        ],
        default='manual',
        verbose_name="调度类型"
    )
    interval_seconds = models.IntegerField(null=True, blank=True, verbose_name="执行间隔(秒)")
    
    # 结果处理
    result_parser = models.CharField(max_length=100, blank=True, verbose_name="结果解析器")
    result_format = models.CharField(
        max_length=20,
        choices=[
            ('json', 'JSON'),
            ('xml', 'XML'),
            ('text', '纯文本'),
            ('csv', 'CSV'),
        ],
        default='text',
        verbose_name="结果格式"
    )
    
    # 其他配置
    tags = models.JSONField(default=list, verbose_name="标签")
    variables = models.JSONField(default=dict, verbose_name="变量定义")
    
    is_active = models.BooleanField(default=True, verbose_name="是否激活")
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name="创建者"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = 'task_templates'
        verbose_name = "任务模板"
        verbose_name_plural = "任务模板"

    def __str__(self):
        return self.name


class CollectionTask(models.Model):
    """采集任务模型"""
    STATUS_CHOICES = [
        ('pending', '待执行'),
        ('running', '执行中'),
        ('success', '成功'),
        ('failed', '失败'),
        ('timeout', '超时'),
        ('cancelled', '已取消'),
        ('paused', '已暂停'),
    ]

    PRIORITY_CHOICES = [
        ('low', '低'),
        ('normal', '普通'),
        ('high', '高'),
        ('urgent', '紧急'),
    ]

    name = models.CharField(max_length=100, verbose_name="任务名称")
    description = models.TextField(blank=True, verbose_name="任务描述")
    template = models.ForeignKey(
        TaskTemplate, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="任务模板"
    )
    
    # 目标设备
    target_devices = models.ManyToManyField(
        Device, 
        blank=True, 
        verbose_name="目标设备"
    )
    target_groups = models.ManyToManyField(
        DeviceGroup, 
        blank=True, 
        verbose_name="目标设备组"
    )
    device_filter = models.JSONField(default=dict, verbose_name="设备过滤条件")
    
    # 执行配置
    command = models.TextField(verbose_name="执行命令")
    timeout = models.IntegerField(default=30, verbose_name="超时时间(秒)")
    retry_count = models.IntegerField(default=3, verbose_name="重试次数")
    retry_interval = models.IntegerField(default=5, verbose_name="重试间隔(秒)")
    
    # 调度配置
    schedule_type = models.CharField(
        max_length=20,
        choices=TaskTemplate._meta.get_field('schedule_type').choices,
        default='manual',
        verbose_name="调度类型"
    )
    cron_expression = models.CharField(max_length=100, blank=True, verbose_name="CRON表达式")
    interval_seconds = models.IntegerField(null=True, blank=True, verbose_name="执行间隔(秒)")
    next_run_time = models.DateTimeField(null=True, blank=True, verbose_name="下次执行时间")
    
    # 任务状态
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending', 
        verbose_name="任务状态"
    )
    priority = models.CharField(
        max_length=20, 
        choices=PRIORITY_CHOICES, 
        default='normal', 
        verbose_name="优先级"
    )
    
    # 执行统计
    total_executions = models.IntegerField(default=0, verbose_name="总执行次数")
    success_executions = models.IntegerField(default=0, verbose_name="成功执行次数")
    failed_executions = models.IntegerField(default=0, verbose_name="失败执行次数")
    
    # XXL-Job相关
    xxl_job_id = models.IntegerField(null=True, blank=True, verbose_name="XXL-Job任务ID")
    xxl_job_group = models.IntegerField(default=1, verbose_name="XXL-Job执行器组")
    
    # 其他配置
    tags = models.JSONField(default=list, verbose_name="标签")
    variables = models.JSONField(default=dict, verbose_name="任务变量")
    notification_config = models.JSONField(default=dict, verbose_name="通知配置")
    
    is_active = models.BooleanField(default=True, verbose_name="是否激活")
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name="创建者"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = 'collection_tasks'
        verbose_name = "采集任务"
        verbose_name_plural = "采集任务"

    def __str__(self):
        return self.name

    @property
    def success_rate(self):
        """成功率"""
        if self.total_executions == 0:
            return 0
        return round((self.success_executions / self.total_executions) * 100, 2)

    def get_target_devices(self):
        """获取所有目标设备"""
        devices = set(self.target_devices.all())
        
        # 添加设备组中的设备
        for group in self.target_groups.all():
            devices.update(group.device_set.all())
        
        # 应用设备过滤条件
        if self.device_filter:
            # 这里可以根据filter条件进一步过滤设备
            pass
            
        return list(devices)


class TaskExecution(models.Model):
    """任务执行记录模型"""
    STATUS_CHOICES = CollectionTask.STATUS_CHOICES

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
    collector = models.ForeignKey(
        Collector, 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name="执行采集器"
    )
    
    # 执行信息
    execution_id = models.CharField(max_length=100, unique=True, verbose_name="执行ID")
    command = models.TextField(verbose_name="执行命令")
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending', 
        verbose_name="执行状态"
    )
    
    # 时间信息
    start_time = models.DateTimeField(null=True, blank=True, verbose_name="开始时间")
    end_time = models.DateTimeField(null=True, blank=True, verbose_name="结束时间")
    duration = models.FloatField(null=True, blank=True, verbose_name="执行时长(秒)")
    
    # 结果信息
    result_data = models.TextField(blank=True, verbose_name="执行结果")
    error_message = models.TextField(blank=True, verbose_name="错误信息")
    exit_code = models.IntegerField(null=True, blank=True, verbose_name="退出码")
    
    # 重试信息
    retry_count = models.IntegerField(default=0, verbose_name="重试次数")
    max_retries = models.IntegerField(default=3, verbose_name="最大重试次数")
    
    # XXL-Job相关
    xxl_job_log_id = models.BigIntegerField(null=True, blank=True, verbose_name="XXL-Job日志ID")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = 'task_executions'
        verbose_name = "任务执行记录"
        verbose_name_plural = "任务执行记录"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.task.name} - {self.device.name} - {self.status}"

    @property
    def is_completed(self):
        """是否已完成"""
        return self.status in ['success', 'failed', 'timeout', 'cancelled']

    @property
    def can_retry(self):
        """是否可以重试"""
        return (
            self.status in ['failed', 'timeout'] and 
            self.retry_count < self.max_retries
        )
