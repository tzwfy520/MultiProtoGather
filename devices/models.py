from django.db import models
from django.contrib.auth import get_user_model
from cryptography.fernet import Fernet
from django.conf import settings
import json

User = get_user_model()


class DeviceGroup(models.Model):
    """设备分组模型"""
    name = models.CharField(max_length=100, unique=True, verbose_name="分组名称")
    description = models.TextField(blank=True, verbose_name="分组描述")
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        verbose_name="父分组"
    )
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name="创建者"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = 'device_groups'
        verbose_name = "设备分组"
        verbose_name_plural = "设备分组"

    def __str__(self):
        return self.name

    def get_full_path(self):
        """获取完整路径"""
        if self.parent:
            return f"{self.parent.get_full_path()}/{self.name}"
        return self.name


class Device(models.Model):
    """设备模型"""
    PROTOCOL_CHOICES = [
        ('ssh', 'SSH'),
        ('snmp', 'SNMP'),
        ('api', 'API'),
        ('telnet', 'Telnet'),
        ('ftp', 'FTP'),
        ('sftp', 'SFTP'),
    ]

    STATUS_CHOICES = [
        ('online', '在线'),
        ('offline', '离线'),
        ('unknown', '未知'),
        ('error', '错误'),
    ]

    name = models.CharField(max_length=100, verbose_name="设备名称")
    ip_address = models.GenericIPAddressField(verbose_name="IP地址")
    port = models.IntegerField(default=22, verbose_name="端口")
    protocol = models.CharField(
        max_length=20, 
        choices=PROTOCOL_CHOICES, 
        verbose_name="协议类型"
    )
    group = models.ForeignKey(
        DeviceGroup, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="设备分组"
    )
    location = models.CharField(max_length=200, blank=True, verbose_name="设备位置")
    vendor = models.CharField(max_length=100, blank=True, verbose_name="厂商")
    model = models.CharField(max_length=100, blank=True, verbose_name="型号")
    os_version = models.CharField(max_length=100, blank=True, verbose_name="系统版本")
    description = models.TextField(blank=True, verbose_name="设备描述")
    
    # 认证信息（加密存储）
    username = models.CharField(max_length=100, blank=True, verbose_name="用户名")
    password = models.TextField(blank=True, verbose_name="密码（加密）")
    private_key = models.TextField(blank=True, verbose_name="私钥（加密）")
    
    # 协议特定参数
    protocol_params = models.JSONField(default=dict, verbose_name="协议参数")
    
    # 状态信息
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='unknown', 
        verbose_name="设备状态"
    )
    last_check_time = models.DateTimeField(null=True, blank=True, verbose_name="最后检查时间")
    response_time = models.FloatField(null=True, blank=True, verbose_name="响应时间(ms)")
    
    # 标签和元数据
    tags = models.JSONField(default=list, verbose_name="标签")
    metadata = models.JSONField(default=dict, verbose_name="元数据")
    
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
        db_table = 'devices'
        verbose_name = "设备"
        verbose_name_plural = "设备"
        unique_together = ['ip_address', 'port', 'protocol']

    def __str__(self):
        return f"{self.name} ({self.ip_address}:{self.port})"

    def encrypt_field(self, value):
        """加密字段值"""
        if not value:
            return ""
        key = settings.ENCRYPTION_KEY.encode()
        f = Fernet(key)
        return f.encrypt(value.encode()).decode()

    def decrypt_field(self, encrypted_value):
        """解密字段值"""
        if not encrypted_value:
            return ""
        key = settings.ENCRYPTION_KEY.encode()
        f = Fernet(key)
        return f.decrypt(encrypted_value.encode()).decode()

    def set_password(self, password):
        """设置加密密码"""
        self.password = self.encrypt_field(password)

    def get_password(self):
        """获取解密密码"""
        return self.decrypt_field(self.password)

    def set_private_key(self, private_key):
        """设置加密私钥"""
        self.private_key = self.encrypt_field(private_key)

    def get_private_key(self):
        """获取解密私钥"""
        return self.decrypt_field(self.private_key)

    def get_connection_params(self):
        """获取连接参数"""
        params = {
            'host': self.ip_address,
            'port': self.port,
            'username': self.username,
            'protocol': self.protocol,
        }
        
        if self.password:
            params['password'] = self.get_password()
        
        if self.private_key:
            params['private_key'] = self.get_private_key()
            
        params.update(self.protocol_params)
        return params


class DeviceStatusHistory(models.Model):
    """设备状态历史记录"""
    device = models.ForeignKey(
        Device, 
        on_delete=models.CASCADE, 
        verbose_name="设备"
    )
    status = models.CharField(
        max_length=20, 
        choices=Device.STATUS_CHOICES, 
        verbose_name="状态"
    )
    response_time = models.FloatField(null=True, blank=True, verbose_name="响应时间(ms)")
    error_message = models.TextField(blank=True, verbose_name="错误信息")
    check_time = models.DateTimeField(auto_now_add=True, verbose_name="检查时间")

    class Meta:
        db_table = 'device_status_history'
        verbose_name = "设备状态历史"
        verbose_name_plural = "设备状态历史"
        ordering = ['-check_time']

    def __str__(self):
        return f"{self.device.name} - {self.status} - {self.check_time}"
