from django.db import models
from django.contrib.auth import get_user_model
from devices.models import Device
from tasks.models import CollectionTask
from results.models import CollectionResult
import json

User = get_user_model()


class AlertRule(models.Model):
    """告警规则模型"""
    RULE_TYPE = [
        ('threshold', '阈值告警'),
        ('pattern', '模式匹配'),
        ('anomaly', '异常检测'),
        ('status', '状态告警'),
        ('timeout', '超时告警'),
    ]

    SEVERITY = [
        ('critical', '严重'),
        ('high', '高'),
        ('medium', '中'),
        ('low', '低'),
        ('info', '信息'),
    ]

    OPERATOR = [
        ('gt', '大于'),
        ('gte', '大于等于'),
        ('lt', '小于'),
        ('lte', '小于等于'),
        ('eq', '等于'),
        ('ne', '不等于'),
        ('contains', '包含'),
        ('not_contains', '不包含'),
        ('regex', '正则匹配'),
    ]

    name = models.CharField(max_length=100, verbose_name="规则名称")
    description = models.TextField(blank=True, verbose_name="规则描述")
    rule_type = models.CharField(
        max_length=20, 
        choices=RULE_TYPE, 
        verbose_name="规则类型"
    )
    severity = models.CharField(
        max_length=20, 
        choices=SEVERITY, 
        verbose_name="告警级别"
    )
    
    # 规则范围
    tasks = models.ManyToManyField(
        CollectionTask, 
        blank=True, 
        verbose_name="关联任务"
    )
    devices = models.ManyToManyField(
        Device, 
        blank=True, 
        verbose_name="关联设备"
    )
    device_groups = models.JSONField(default=list, verbose_name="设备组")
    
    # 规则条件
    conditions = models.JSONField(default=dict, verbose_name="告警条件")
    threshold_value = models.FloatField(null=True, blank=True, verbose_name="阈值")
    operator = models.CharField(
        max_length=20, 
        choices=OPERATOR, 
        null=True, 
        blank=True, 
        verbose_name="比较操作符"
    )
    pattern = models.TextField(blank=True, verbose_name="匹配模式")
    
    # 规则配置
    enabled = models.BooleanField(default=True, verbose_name="是否启用")
    check_interval = models.IntegerField(default=300, verbose_name="检查间隔(秒)")
    consecutive_count = models.IntegerField(default=1, verbose_name="连续触发次数")
    recovery_condition = models.JSONField(default=dict, verbose_name="恢复条件")
    
    # 抑制配置
    suppression_duration = models.IntegerField(default=3600, verbose_name="抑制时长(秒)")
    max_alerts_per_hour = models.IntegerField(default=10, verbose_name="每小时最大告警数")
    
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name="创建者"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = 'alert_rules'
        verbose_name = "告警规则"
        verbose_name_plural = "告警规则"
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def check_condition(self, result_data):
        """检查告警条件"""
        if not self.enabled:
            return False
            
        # 根据规则类型检查条件
        if self.rule_type == 'threshold':
            return self._check_threshold(result_data)
        elif self.rule_type == 'pattern':
            return self._check_pattern(result_data)
        elif self.rule_type == 'status':
            return self._check_status(result_data)
        
        return False

    def _check_threshold(self, result_data):
        """检查阈值条件"""
        if not self.threshold_value or not self.operator:
            return False
            
        # 从结果数据中提取数值
        value = self._extract_numeric_value(result_data)
        if value is None:
            return False
            
        # 执行比较操作
        if self.operator == 'gt':
            return value > self.threshold_value
        elif self.operator == 'gte':
            return value >= self.threshold_value
        elif self.operator == 'lt':
            return value < self.threshold_value
        elif self.operator == 'lte':
            return value <= self.threshold_value
        elif self.operator == 'eq':
            return value == self.threshold_value
        elif self.operator == 'ne':
            return value != self.threshold_value
            
        return False

    def _check_pattern(self, result_data):
        """检查模式匹配"""
        if not self.pattern:
            return False
            
        import re
        text_data = str(result_data)
        
        if self.operator == 'contains':
            return self.pattern in text_data
        elif self.operator == 'not_contains':
            return self.pattern not in text_data
        elif self.operator == 'regex':
            return bool(re.search(self.pattern, text_data))
            
        return False

    def _check_status(self, result_data):
        """检查状态条件"""
        if isinstance(result_data, dict):
            status = result_data.get('status')
            return status in self.conditions.get('status_list', [])
        return False

    def _extract_numeric_value(self, result_data):
        """从结果数据中提取数值"""
        if isinstance(result_data, (int, float)):
            return result_data
            
        if isinstance(result_data, dict):
            field_path = self.conditions.get('field_path', '')
            if field_path:
                try:
                    value = result_data
                    for key in field_path.split('.'):
                        value = value[key]
                    return float(value)
                except (KeyError, ValueError, TypeError):
                    pass
                    
        return None


class Alert(models.Model):
    """告警记录模型"""
    ALERT_STATUS = [
        ('active', '活跃'),
        ('acknowledged', '已确认'),
        ('resolved', '已解决'),
        ('suppressed', '已抑制'),
        ('expired', '已过期'),
    ]

    rule = models.ForeignKey(
        AlertRule, 
        on_delete=models.CASCADE, 
        verbose_name="告警规则"
    )
    task = models.ForeignKey(
        CollectionTask, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        verbose_name="关联任务"
    )
    device = models.ForeignKey(
        Device, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        verbose_name="关联设备"
    )
    result = models.ForeignKey(
        CollectionResult, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        verbose_name="关联结果"
    )
    
    # 告警信息
    title = models.CharField(max_length=200, verbose_name="告警标题")
    message = models.TextField(verbose_name="告警消息")
    severity = models.CharField(
        max_length=20, 
        choices=AlertRule.SEVERITY, 
        verbose_name="告警级别"
    )
    status = models.CharField(
        max_length=20, 
        choices=ALERT_STATUS, 
        default='active', 
        verbose_name="告警状态"
    )
    
    # 告警数据
    trigger_data = models.JSONField(default=dict, verbose_name="触发数据")
    context_data = models.JSONField(default=dict, verbose_name="上下文数据")
    
    # 时间信息
    first_occurred_at = models.DateTimeField(verbose_name="首次发生时间")
    last_occurred_at = models.DateTimeField(verbose_name="最后发生时间")
    acknowledged_at = models.DateTimeField(null=True, blank=True, verbose_name="确认时间")
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="解决时间")
    
    # 处理信息
    acknowledged_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='acknowledged_alerts',
        verbose_name="确认人"
    )
    resolved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='resolved_alerts',
        verbose_name="解决人"
    )
    
    # 统计信息
    occurrence_count = models.IntegerField(default=1, verbose_name="发生次数")
    notification_count = models.IntegerField(default=0, verbose_name="通知次数")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = 'alerts'
        verbose_name = "告警记录"
        verbose_name_plural = "告警记录"
        ordering = ['-last_occurred_at']

    def __str__(self):
        return f"{self.title} - {self.severity} - {self.status}"

    def acknowledge(self, user):
        """确认告警"""
        self.status = 'acknowledged'
        self.acknowledged_by = user
        self.acknowledged_at = models.timezone.now()
        self.save()

    def resolve(self, user):
        """解决告警"""
        self.status = 'resolved'
        self.resolved_by = user
        self.resolved_at = models.timezone.now()
        self.save()

    @property
    def duration(self):
        """告警持续时间"""
        if self.resolved_at:
            return self.resolved_at - self.first_occurred_at
        return models.timezone.now() - self.first_occurred_at


class NotificationChannel(models.Model):
    """通知渠道模型"""
    CHANNEL_TYPE = [
        ('email', '邮件'),
        ('dingtalk', '钉钉'),
        ('wechat', '微信'),
        ('sms', '短信'),
        ('webhook', 'Webhook'),
        ('slack', 'Slack'),
    ]

    name = models.CharField(max_length=100, verbose_name="渠道名称")
    description = models.TextField(blank=True, verbose_name="渠道描述")
    channel_type = models.CharField(
        max_length=20, 
        choices=CHANNEL_TYPE, 
        verbose_name="渠道类型"
    )
    
    # 渠道配置
    config = models.JSONField(default=dict, verbose_name="渠道配置")
    
    # 发送配置
    enabled = models.BooleanField(default=True, verbose_name="是否启用")
    rate_limit = models.IntegerField(default=60, verbose_name="速率限制(次/小时)")
    retry_count = models.IntegerField(default=3, verbose_name="重试次数")
    timeout = models.IntegerField(default=30, verbose_name="超时时间(秒)")
    
    # 过滤条件
    severity_filter = models.JSONField(default=list, verbose_name="级别过滤")
    time_filter = models.JSONField(default=dict, verbose_name="时间过滤")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = 'notification_channels'
        verbose_name = "通知渠道"
        verbose_name_plural = "通知渠道"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_channel_type_display()})"

    def can_send(self, alert):
        """检查是否可以发送通知"""
        if not self.enabled:
            return False
            
        # 检查级别过滤
        if self.severity_filter and alert.severity not in self.severity_filter:
            return False
            
        # 检查时间过滤
        if self.time_filter:
            # 实现时间过滤逻辑
            pass
            
        return True


class NotificationLog(models.Model):
    """通知日志模型"""
    SEND_STATUS = [
        ('pending', '待发送'),
        ('sending', '发送中'),
        ('success', '成功'),
        ('failed', '失败'),
        ('retry', '重试中'),
    ]

    alert = models.ForeignKey(
        Alert, 
        on_delete=models.CASCADE, 
        verbose_name="关联告警"
    )
    channel = models.ForeignKey(
        NotificationChannel, 
        on_delete=models.CASCADE, 
        verbose_name="通知渠道"
    )
    
    # 发送信息
    status = models.CharField(
        max_length=20, 
        choices=SEND_STATUS, 
        default='pending', 
        verbose_name="发送状态"
    )
    recipients = models.JSONField(default=list, verbose_name="接收者")
    subject = models.CharField(max_length=200, blank=True, verbose_name="主题")
    content = models.TextField(verbose_name="通知内容")
    
    # 结果信息
    response_data = models.JSONField(null=True, blank=True, verbose_name="响应数据")
    error_message = models.TextField(blank=True, verbose_name="错误信息")
    retry_count = models.IntegerField(default=0, verbose_name="重试次数")
    
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="发送时间")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = 'notification_logs'
        verbose_name = "通知日志"
        verbose_name_plural = "通知日志"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.alert.title} - {self.channel.name} - {self.status}"
