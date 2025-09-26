from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import login, logout
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
from .models import User, Role, OperationLog
from .serializers import (
    UserSerializer, UserProfileSerializer, RoleSerializer,
    ChangePasswordSerializer, LoginSerializer, OperationLogSerializer,
    UserStatsSerializer
)


class LoginView(APIView):
    """用户登录视图"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # 生成JWT令牌
            refresh = RefreshToken.for_user(user)
            
            # 记录登录日志
            OperationLog.objects.create(
                user=user,
                action='login',
                description='用户登录',
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserProfileSerializer(user).data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get_client_ip(self, request):
        """获取客户端IP地址"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class LogoutView(APIView):
    """用户登出视图"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            # 记录登出日志
            OperationLog.objects.create(
                user=request.user,
                action='logout',
                description='用户登出',
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return Response({"message": "登出成功"})
        except Exception as e:
            return Response({"error": "登出失败"}, status=status.HTTP_400_BAD_REQUEST)
    
    def get_client_ip(self, request):
        """获取客户端IP地址"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class UserListCreateView(generics.ListCreateAPIView):
    """用户列表和创建视图"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = User.objects.select_related('role').all()
        
        # 搜索过滤
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(department__icontains=search)
            )
        
        # 角色过滤
        role_id = self.request.query_params.get('role')
        if role_id:
            queryset = queryset.filter(role_id=role_id)
        
        # 状态过滤
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset.order_by('-date_joined')
    
    def perform_create(self, serializer):
        user = serializer.save()
        
        # 记录操作日志
        OperationLog.objects.create(
            user=self.request.user,
            action='create',
            resource_type='user',
            resource_id=user.id,
            resource_name=user.username,
            description=f'创建用户: {user.username}',
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )
    
    def get_client_ip(self):
        """获取客户端IP地址"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """用户详情视图"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_update(self, serializer):
        user = serializer.save()
        
        # 记录操作日志
        OperationLog.objects.create(
            user=self.request.user,
            action='update',
            resource_type='user',
            resource_id=user.id,
            resource_name=user.username,
            description=f'更新用户: {user.username}',
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )
    
    def perform_destroy(self, instance):
        # 记录操作日志
        OperationLog.objects.create(
            user=self.request.user,
            action='delete',
            resource_type='user',
            resource_id=instance.id,
            resource_name=instance.username,
            description=f'删除用户: {instance.username}',
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )
        
        instance.delete()
    
    def get_client_ip(self):
        """获取客户端IP地址"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class UserProfileView(generics.RetrieveUpdateAPIView):
    """用户资料视图"""
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    """修改密码视图"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            # 记录操作日志
            OperationLog.objects.create(
                user=user,
                action='update',
                resource_type='user',
                resource_id=user.id,
                resource_name=user.username,
                description='修改密码',
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return Response({"message": "密码修改成功"})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get_client_ip(self, request):
        """获取客户端IP地址"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class RoleListCreateView(generics.ListCreateAPIView):
    """角色列表和创建视图"""
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = Role.objects.all()
        
        # 搜索过滤
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
        
        return queryset.order_by('name')
    
    def perform_create(self, serializer):
        role = serializer.save()
        
        # 记录操作日志
        OperationLog.objects.create(
            user=self.request.user,
            action='create',
            resource_type='role',
            resource_id=role.id,
            resource_name=role.name,
            description=f'创建角色: {role.name}',
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )
    
    def get_client_ip(self):
        """获取客户端IP地址"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class RoleDetailView(generics.RetrieveUpdateDestroyAPIView):
    """角色详情视图"""
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_update(self, serializer):
        role = serializer.save()
        
        # 记录操作日志
        OperationLog.objects.create(
            user=self.request.user,
            action='update',
            resource_type='role',
            resource_id=role.id,
            resource_name=role.name,
            description=f'更新角色: {role.name}',
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )
    
    def perform_destroy(self, instance):
        # 检查是否有用户使用该角色
        if instance.user_set.exists():
            return Response(
                {"error": "无法删除正在使用的角色"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 记录操作日志
        OperationLog.objects.create(
            user=self.request.user,
            action='delete',
            resource_type='role',
            resource_id=instance.id,
            resource_name=instance.name,
            description=f'删除角色: {instance.name}',
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )
        
        instance.delete()
    
    def get_client_ip(self):
        """获取客户端IP地址"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class OperationLogListView(generics.ListAPIView):
    """操作日志列表视图"""
    queryset = OperationLog.objects.all()
    serializer_class = OperationLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = OperationLog.objects.select_related('user').all()
        
        # 用户过滤
        user_id = self.request.query_params.get('user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # 操作类型过滤
        action = self.request.query_params.get('action')
        if action:
            queryset = queryset.filter(action=action)
        
        # 资源类型过滤
        resource_type = self.request.query_params.get('resource_type')
        if resource_type:
            queryset = queryset.filter(resource_type=resource_type)
        
        # 时间范围过滤
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        return queryset.order_by('-created_at')


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_stats(request):
    """用户统计视图"""
    today = timezone.now().date()
    
    # 统计数据
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    inactive_users = total_users - active_users
    
    # 今日新增用户
    new_users_today = User.objects.filter(date_joined__date=today).count()
    
    # 在线用户（最近15分钟有活动）
    online_threshold = timezone.now() - timedelta(minutes=15)
    online_users = User.objects.filter(last_login__gte=online_threshold).count()
    
    # 角色数量
    roles_count = Role.objects.count()
    
    stats_data = {
        'total_users': total_users,
        'active_users': active_users,
        'inactive_users': inactive_users,
        'online_users': online_users,
        'new_users_today': new_users_today,
        'roles_count': roles_count,
    }
    
    serializer = UserStatsSerializer(stats_data)
    return Response(serializer.data)
