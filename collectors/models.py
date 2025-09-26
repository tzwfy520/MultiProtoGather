from django.db import models
from django.contrib.auth import get_user_model
from devices.models import Device
import json

User = get_user_model()


class ServiceZone(models.Model):
    """服务区模型"""
    name = models.CharField(max_length=100, unique=True, verbose_name="服务区名称")
    description = models.TextField(blank=True, verbose_name="服务区描述")
    ssh_host = models.GenericIPAddressField(verbose_name="SSH主机地址")
    ssh_port = models.IntegerField(default=22, verbose_name="SSH端口")
    ssh_username = models.CharField(max_length=100, verbose_name="SSH用户名")
    ssh_password = models.TextField(blank=True, verbose_name="SSH密码（加密）")
    ssh_private_key = models.TextField(blank=True, verbose_name="SSH私钥（加密）")
    
    # 服务器信息
    os_type = models.CharField(max_length=50, blank=True, verbose_name="操作系统类型")
    os_version = models.CharField(max_length=100, blank=True, verbose_name="操作系统版本")
    cpu_cores = models.IntegerField(null=True, blank=True, verbose_name="CPU核心数")
    memory_gb = models.FloatField(null=True, blank=True, verbose_name="内存(GB)")
    disk_gb = models.FloatField(null=True, blank=True, verbose_name="磁盘(GB)")
    
    # 状态信息
    status = models.CharField(
        max_length=20,
        choices=[
            ('online', '在线'),
            ('offline', '离线'),
            ('unknown', '未知'),
            ('error', '错误'),
        ],
        default='unknown',
        verbose_name="状态"
    )
    last_heartbeat = models.DateTimeField(null=True, blank=True, verbose_name="最后心跳时间")
    
    # 配置信息
    docker_installed = models.BooleanField(default=False, verbose_name="Docker已安装")
    collector_path = models.CharField(
        max_length=500, 
        default='/opt/collectors', 
        verbose_name="采集器安装路径"
    )
    
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
        db_table = 'service_zones'
        verbose_name = "服务区"
        verbose_name_plural = "服务区"

    def __str__(self):
        return self.name


class Collector(models.Model):
    """采集器模型"""
    COLLECTOR_TYPES = [
        ('ssh_python', 'Python SSH采集器'),
        ('ssh_go', 'Go SSH采集器'),
        ('snmp_python', 'Python SNMP采集器'),
        ('api_python', 'Python API采集器'),
        ('custom', '自定义采集器'),
    ]

    STATUS_CHOICES = [
        ('online', '在线'),
        ('offline', '离线'),
        ('busy', '忙碌'),
        ('error', '错误'),
        ('unknown', '未知'),
    ]

    name = models.CharField(max_length=100, verbose_name="采集器名称")
    collector_type = models.CharField(
        max_length=50, 
        choices=COLLECTOR_TYPES, 
        verbose_name="采集器类型"
    )
    version = models.CharField(max_length=50, verbose_name="版本号")
    service_zone = models.ForeignKey(
        ServiceZone, 
        on_delete=models.CASCADE, 
        verbose_name="服务区"
    )
    
    # 网络信息
    host = models.GenericIPAddressField(verbose_name="主机地址")
    port = models.IntegerField(verbose_name="端口")
    api_endpoint = models.URLField(blank=True, verbose_name="API端点")
    
    # 配置信息
    max_concurrent_tasks = models.IntegerField(default=10, verbose_name="最大并发任务数")
    supported_protocols = models.JSONField(default=list, verbose_name="支持的协议")
    config_params = models.JSONField(default=dict, verbose_name="配置参数")
    
    # 状态信息
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='unknown', 
        verbose_name="状态"
    )
    current_tasks = models.IntegerField(default=0, verbose_name="当前任务数")
    total_tasks = models.IntegerField(default=0, verbose_name="总任务数")
    success_tasks = models.IntegerField(default=0, verbose_name="成功任务数")
    failed_tasks = models.IntegerField(default=0, verbose_name="失败任务数")
    
    # 性能指标
    cpu_usage = models.FloatField(null=True, blank=True, verbose_name="CPU使用率(%)")
    memory_usage = models.FloatField(null=True, blank=True, verbose_name="内存使用率(%)")
    avg_response_time = models.FloatField(null=True, blank=True, verbose_name="平均响应时间(ms)")
    
    # 时间信息
    last_heartbeat = models.DateTimeField(null=True, blank=True, verbose_name="最后心跳时间")
    last_task_time = models.DateTimeField(null=True, blank=True, verbose_name="最后任务时间")
    
    # 标签和分组
    tags = models.JSONField(default=list, verbose_name="标签")
    group_name = models.CharField(max_length=100, blank=True, verbose_name="分组名称")
    
    is_active = models.BooleanField(default=True, verbose_name="是否激活")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = 'collectors'
        verbose_name = "采集器"
        verbose_name_plural = "采集器"
        unique_together = ['host', 'port']

    def __str__(self):
        return f"{self.name} ({self.host}:{self.port})"

    @property
    def success_rate(self):
        """成功率"""
        if self.total_tasks == 0:
            return 0
        return round((self.success_tasks / self.total_tasks) * 100, 2)

    def can_accept_task(self):
        """是否可以接受新任务"""
        return (
            self.status == 'online' and 
            self.current_tasks < self.max_concurrent_tasks and
            self.is_active
        )

    def supports_protocol(self, protocol):
        """是否支持指定协议"""
        return protocol in self.supported_protocols


class CollectorPerformance(models.Model):
    """采集器性能记录"""
    collector = models.ForeignKey(
        Collector, 
        on_delete=models.CASCADE, 
        verbose_name="采集器"
    )
    cpu_usage = models.FloatField(verbose_name="CPU使用率(%)")
    memory_usage = models.FloatField(verbose_name="内存使用率(%)")
    disk_usage = models.FloatField(null=True, blank=True, verbose_name="磁盘使用率(%)")
    network_in = models.FloatField(null=True, blank=True, verbose_name="网络入流量(MB/s)")
    network_out = models.FloatField(null=True, blank=True, verbose_name="网络出流量(MB/s)")
    active_connections = models.IntegerField(null=True, blank=True, verbose_name="活跃连接数")
    response_time = models.FloatField(null=True, blank=True, verbose_name="响应时间(ms)")
    recorded_at = models.DateTimeField(auto_now_add=True, verbose_name="记录时间")

    class Meta:
        db_table = 'collector_performance'
        verbose_name = "采集器性能"
        verbose_name_plural = "采集器性能"
        ordering = ['-recorded_at']

    def __str__(self):
        return f"{self.collector.name} - {self.recorded_at}"


class CollectorDeployment(models.Model):
    """采集器部署记录"""
    DEPLOYMENT_STATUS = [
        ('pending', '待部署'),
        ('deploying', '部署中'),
        ('success', '部署成功'),
        ('failed', '部署失败'),
        ('stopped', '已停止'),
    ]

    service_zone = models.ForeignKey(
        ServiceZone, 
        on_delete=models.CASCADE, 
        verbose_name="服务区"
    )
    collector_type = models.CharField(
        max_length=50, 
        choices=Collector.COLLECTOR_TYPES, 
        verbose_name="采集器类型"
    )
    image_name = models.CharField(max_length=200, verbose_name="镜像名称")
    image_tag = models.CharField(max_length=50, verbose_name="镜像标签")
    container_name = models.CharField(max_length=100, verbose_name="容器名称")
    
    # 部署配置
    port_mapping = models.JSONField(default=dict, verbose_name="端口映射")
    environment_vars = models.JSONField(default=dict, verbose_name="环境变量")
    volume_mapping = models.JSONField(default=dict, verbose_name="卷映射")
    
    # 部署状态
    status = models.CharField(
        max_length=20, 
        choices=DEPLOYMENT_STATUS, 
        default='pending', 
        verbose_name="部署状态"
    )
    container_id = models.CharField(max_length=100, blank=True, verbose_name="容器ID")
    deploy_log = models.TextField(blank=True, verbose_name="部署日志")
    error_message = models.TextField(blank=True, verbose_name="错误信息")
    
    deployed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name="部署者"
    )
    deployed_at = models.DateTimeField(null=True, blank=True, verbose_name="部署时间")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = 'collector_deployments'
        verbose_name = "采集器部署"
        verbose_name_plural = "采集器部署"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.collector_type} - {self.service_zone.name} - {self.status}"
