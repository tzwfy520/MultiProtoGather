from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class Role(models.Model):
    """角色模型"""
    name = models.CharField(max_length=50, unique=True, verbose_name="角色名称")
    description = models.TextField(blank=True, verbose_name="角色描述")
    permissions = models.JSONField(default=list, verbose_name="权限列表")
    is_active = models.BooleanField(default=True, verbose_name="是否激活")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = 'roles'
        verbose_name = "角色"
        verbose_name_plural = "角色"

    def __str__(self):
        return self.name


class User(AbstractUser):
    """用户模型"""
    phone = models.CharField(max_length=20, blank=True, verbose_name="手机号")
    department = models.CharField(max_length=100, blank=True, verbose_name="部门")
    position = models.CharField(max_length=100, blank=True, verbose_name="职位")
    role = models.ForeignKey(
        Role, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="角色"
    )
    last_login_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name="最后登录IP")
    is_active = models.BooleanField(default=True, verbose_name="是否激活")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = 'users'
        verbose_name = "用户"
        verbose_name_plural = "用户"

    def __str__(self):
        return self.username

    def has_permission(self, permission):
        """检查用户是否有指定权限"""
        if self.is_superuser:
            return True
        if self.role and self.role.is_active:
            return permission in self.role.permissions
        return False


class OperationLog(models.Model):
    """操作日志模型"""
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name="操作用户"
    )
    action = models.CharField(max_length=100, verbose_name="操作动作")
    resource_type = models.CharField(max_length=50, verbose_name="资源类型")
    resource_id = models.CharField(max_length=100, blank=True, verbose_name="资源ID")
    description = models.TextField(verbose_name="操作描述")
    ip_address = models.GenericIPAddressField(verbose_name="IP地址")
    user_agent = models.TextField(blank=True, verbose_name="用户代理")
    result = models.CharField(
        max_length=20, 
        choices=[('success', '成功'), ('failed', '失败')],
        verbose_name="操作结果"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = 'operation_logs'
        verbose_name = "操作日志"
        verbose_name_plural = "操作日志"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} - {self.action} - {self.created_at}"
