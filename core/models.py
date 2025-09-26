from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings


User = get_user_model()


class OperationLog(models.Model):
    """操作日志模型"""
    
    ACTION_CHOICES = [
        ('create', '创建'),
        ('update', '更新'),
        ('delete', '删除'),
        ('view', '查看'),
        ('export', '导出'),
        ('import', '导入'),
        ('login', '登录'),
        ('logout', '登出'),
        ('other', '其他'),
    ]
    
    LEVEL_CHOICES = [
        ('info', '信息'),
        ('warning', '警告'),
        ('error', '错误'),
        ('debug', '调试'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='core_operation_logs',
        verbose_name='用户'
    )
    action = models.CharField(
        max_length=20, 
        choices=ACTION_CHOICES, 
        default='other',
        verbose_name='操作类型'
    )
    level = models.CharField(
        max_length=10, 
        choices=LEVEL_CHOICES, 
        default='info',
        verbose_name='日志级别'
    )
    module = models.CharField(
        max_length=50, 
        verbose_name='模块名称'
    )
    description = models.TextField(
        verbose_name='操作描述'
    )
    ip_address = models.GenericIPAddressField(
        null=True, 
        blank=True,
        verbose_name='IP地址'
    )
    user_agent = models.TextField(
        null=True, 
        blank=True,
        verbose_name='用户代理'
    )
    extra_data = models.JSONField(
        default=dict, 
        blank=True,
        verbose_name='额外数据'
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='创建时间'
    )
    
    class Meta:
        db_table = 'core_operation_log'
        verbose_name = '操作日志'
        verbose_name_plural = '操作日志'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['action', 'created_at']),
            models.Index(fields=['module', 'created_at']),
            models.Index(fields=['level', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user or 'Anonymous'} - {self.get_action_display()} - {self.module}"
    
    @classmethod
    def log(cls, user=None, action='other', level='info', module='system', 
            description='', ip_address=None, user_agent=None, extra_data=None):
        """便捷的日志记录方法"""
        return cls.objects.create(
            user=user,
            action=action,
            level=level,
            module=module,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            extra_data=extra_data or {}
        )