from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, Role, OperationLog


class RoleSerializer(serializers.ModelSerializer):
    """角色序列化器"""
    permissions_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Role
        fields = ['id', 'name', 'description', 'permissions', 'permissions_display', 
                 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
    
    def get_permissions_display(self, obj):
        """获取权限显示名称"""
        return [perm.replace('_', ' ').title() for perm in obj.permissions]


class UserSerializer(serializers.ModelSerializer):
    """用户序列化器"""
    role_name = serializers.CharField(source='role.name', read_only=True)
    password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 
                 'phone', 'department', 'position', 'role', 'role_name',
                 'is_active', 'is_staff', 'date_joined', 'last_login',
                 'password', 'confirm_password']
        read_only_fields = ['date_joined', 'last_login']
        extra_kwargs = {
            'password': {'write_only': True},
        }
    
    def validate(self, attrs):
        """验证密码确认"""
        if 'password' in attrs and 'confirm_password' in attrs:
            if attrs['password'] != attrs['confirm_password']:
                raise serializers.ValidationError("密码和确认密码不匹配")
        return attrs
    
    def create(self, validated_data):
        """创建用户"""
        validated_data.pop('confirm_password', None)
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user
    
    def update(self, instance, validated_data):
        """更新用户"""
        validated_data.pop('confirm_password', None)
        password = validated_data.pop('password', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if password:
            instance.set_password(password)
        
        instance.save()
        return instance


class UserProfileSerializer(serializers.ModelSerializer):
    """用户资料序列化器"""
    role_name = serializers.CharField(source='role.name', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                 'phone', 'department', 'position', 'role_name']
        read_only_fields = ['username']


class ChangePasswordSerializer(serializers.Serializer):
    """修改密码序列化器"""
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    confirm_password = serializers.CharField(required=True)
    
    def validate(self, attrs):
        """验证密码"""
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError("新密码和确认密码不匹配")
        return attrs
    
    def validate_old_password(self, value):
        """验证旧密码"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("旧密码不正确")
        return value


class LoginSerializer(serializers.Serializer):
    """登录序列化器"""
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True)
    
    def validate(self, attrs):
        """验证登录信息"""
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError("用户名或密码错误")
            if not user.is_active:
                raise serializers.ValidationError("用户账户已被禁用")
            attrs['user'] = user
        else:
            raise serializers.ValidationError("必须提供用户名和密码")
        
        return attrs


class OperationLogSerializer(serializers.ModelSerializer):
    """操作日志序列化器"""
    user_name = serializers.CharField(source='user.username', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = OperationLog
        fields = ['id', 'user', 'user_name', 'action', 'action_display',
                 'resource_type', 'resource_id', 'resource_name',
                 'description', 'ip_address', 'user_agent',
                 'created_at']
        read_only_fields = ['created_at']


class UserStatsSerializer(serializers.Serializer):
    """用户统计序列化器"""
    total_users = serializers.IntegerField()
    active_users = serializers.IntegerField()
    inactive_users = serializers.IntegerField()
    online_users = serializers.IntegerField()
    new_users_today = serializers.IntegerField()
    roles_count = serializers.IntegerField()