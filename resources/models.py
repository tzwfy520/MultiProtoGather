from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from core.utils import encrypt_password, decrypt_password
import json

User = get_user_model()


class ServerResource(models.Model):
    """服务器资源模型"""
    
    STATUS_CHOICES = [
        ('online', '在线'),
        ('offline', '离线'),
        ('checking', '检测中'),
    ]
    
    OS_TYPE_CHOICES = [
        ('linux', 'Linux'),
        ('windows', 'Windows'),
        ('unix', 'Unix'),
        ('other', '其他'),
    ]
    
    # 基本信息
    name = models.CharField(max_length=100, verbose_name='服务器名称', help_text='服务器的显示名称')
    ip_address = models.GenericIPAddressField(verbose_name='IP地址', help_text='服务器的IP地址')
    port = models.PositiveIntegerField(default=22, verbose_name='端口', help_text='SSH连接端口')
    
    # 认证信息
    username = models.CharField(max_length=50, verbose_name='用户名', help_text='SSH登录用户名')
    password = models.CharField(max_length=255, blank=True, null=True, verbose_name='密码', help_text='SSH登录密码（加密存储）')
    private_key = models.TextField(blank=True, null=True, verbose_name='私钥', help_text='SSH私钥内容')
    
    # 系统信息
    os_type = models.CharField(max_length=20, choices=OS_TYPE_CHOICES, default='linux', verbose_name='操作系统类型')
    os_version = models.CharField(max_length=100, blank=True, verbose_name='操作系统版本')
    
    # 状态信息
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='checking', verbose_name='状态')
    last_online_time = models.DateTimeField(null=True, blank=True, verbose_name='最后在线时间')
    response_time = models.FloatField(null=True, blank=True, verbose_name='响应时间(ms)')
    
    # 监控配置
    check_interval = models.PositiveIntegerField(default=300, verbose_name='检查间隔(秒)', help_text='状态检查的时间间隔')
    timeout = models.PositiveIntegerField(default=30, verbose_name='超时时间(秒)', help_text='连接超时时间')
    
    # 分组信息
    group = models.ForeignKey(
        'ServerGroup', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name='服务器组'
    )
    
    # 元数据
    description = models.TextField(blank=True, verbose_name='描述', help_text='服务器描述信息')
    tags = models.JSONField(default=list, verbose_name='标签', help_text='服务器标签列表')
    metadata = models.JSONField(default=dict, verbose_name='元数据', help_text='额外的服务器信息')
    
    # 管理字段
    is_active = models.BooleanField(default=True, verbose_name='是否激活')
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name='创建者'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'server_resources'
        verbose_name = '服务器资源'
        verbose_name_plural = '服务器资源'
        unique_together = ['ip_address', 'port']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['group']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.ip_address})"
    
    def set_password(self, password):
        """设置加密密码"""
        if password:
            self.password = encrypt_password(password)
    
    def get_password(self):
        """获取解密密码"""
        if self.password:
            return decrypt_password(self.password)
        return None
    
    def update_status(self, status, response_time=None, error_message=None):
        """更新服务器状态"""
        old_status = self.status
        self.status = status
        self.response_time = response_time
        
        if status == 'online':
            self.last_online_time = timezone.now()
        
        self.save()
        
        # 记录状态历史
        ServerStatusHistory.objects.create(
            server=self,
            old_status=old_status,
            new_status=status,
            response_time=response_time,
            error_message=error_message
        )


class ServerStatusHistory(models.Model):
    """服务器状态历史记录"""
    
    server = models.ForeignKey(
        ServerResource, 
        on_delete=models.CASCADE, 
        verbose_name='服务器'
    )
    old_status = models.CharField(max_length=20, verbose_name='原状态')
    new_status = models.CharField(max_length=20, verbose_name='新状态')
    response_time = models.FloatField(null=True, blank=True, verbose_name='响应时间(ms)')
    error_message = models.TextField(blank=True, verbose_name='错误信息')
    check_time = models.DateTimeField(auto_now_add=True, verbose_name='检查时间')
    
    class Meta:
        db_table = 'server_status_history'
        verbose_name = '服务器状态历史'
        verbose_name_plural = '服务器状态历史'
        ordering = ['-check_time']
        indexes = [
            models.Index(fields=['server', 'check_time']),
            models.Index(fields=['new_status', 'check_time']),
        ]
    
    def __str__(self):
        return f"{self.server.name} - {self.old_status} -> {self.new_status}"


class ServerGroup(models.Model):
    """服务器分组"""
    
    name = models.CharField(max_length=100, unique=True, verbose_name='分组名称')
    description = models.TextField(blank=True, verbose_name='分组描述')
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        verbose_name='父分组'
    )
    color = models.CharField(max_length=7, default='#1890ff', verbose_name='分组颜色')
    
    # 管理字段
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name='创建者'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'server_groups'
        verbose_name = '服务器分组'
        verbose_name_plural = '服务器分组'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_full_path(self):
        """获取完整路径"""
        if self.parent:
            return f"{self.parent.get_full_path()}/{self.name}"
        return self.name
    
    def get_server_count(self):
        """获取分组下的服务器数量"""
        return self.serverresource_set.count()
    
    def get_online_count(self):
        """获取在线服务器数量"""
        return self.serverresource_set.filter(status='online').count()
