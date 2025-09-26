-- 多协议采集控制器数据库设计
-- 数据库: multiprotgather
-- 字符集: utf8mb4
-- 排序规则: utf8mb4_unicode_ci

-- 用户表
CREATE TABLE `users` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT,
    `username` varchar(150) NOT NULL UNIQUE,
    `email` varchar(254) NOT NULL,
    `password` varchar(128) NOT NULL,
    `first_name` varchar(150) DEFAULT '',
    `last_name` varchar(150) DEFAULT '',
    `is_active` tinyint(1) NOT NULL DEFAULT 1,
    `is_staff` tinyint(1) NOT NULL DEFAULT 0,
    `is_superuser` tinyint(1) NOT NULL DEFAULT 0,
    `date_joined` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `last_login` datetime(6) NULL,
    `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (`id`),
    KEY `idx_username` (`username`),
    KEY `idx_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 角色表
CREATE TABLE `roles` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT,
    `name` varchar(80) NOT NULL UNIQUE,
    `description` text,
    `permissions` json,
    `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (`id`),
    KEY `idx_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 用户角色关联表
CREATE TABLE `user_roles` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT,
    `user_id` bigint(20) NOT NULL,
    `role_id` bigint(20) NOT NULL,
    `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_user_role` (`user_id`, `role_id`),
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`role_id`) REFERENCES `roles` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 设备分组表
CREATE TABLE `device_groups` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT,
    `name` varchar(100) NOT NULL,
    `description` text,
    `parent_id` bigint(20) NULL,
    `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (`id`),
    KEY `idx_name` (`name`),
    KEY `idx_parent_id` (`parent_id`),
    FOREIGN KEY (`parent_id`) REFERENCES `device_groups` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 设备表
CREATE TABLE `devices` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT,
    `name` varchar(100) NOT NULL,
    `ip_address` varchar(45) NOT NULL,
    `device_type` varchar(50) NOT NULL,
    `protocol_type` enum('SSH', 'SNMP', 'API', 'TELNET') NOT NULL,
    `port` int(11) DEFAULT NULL,
    `username` varchar(100) DEFAULT NULL,
    `password` varchar(255) DEFAULT NULL,
    `private_key` text DEFAULT NULL,
    `snmp_community` varchar(100) DEFAULT NULL,
    `snmp_version` enum('v1', 'v2c', 'v3') DEFAULT NULL,
    `api_token` varchar(255) DEFAULT NULL,
    `api_url` varchar(500) DEFAULT NULL,
    `location` varchar(200) DEFAULT NULL,
    `vendor` varchar(100) DEFAULT NULL,
    `model` varchar(100) DEFAULT NULL,
    `os_version` varchar(100) DEFAULT NULL,
    `status` enum('online', 'offline', 'unknown') DEFAULT 'unknown',
    `last_check_time` datetime(6) NULL,
    `group_id` bigint(20) NULL,
    `tags` json DEFAULT NULL,
    `extra_config` json DEFAULT NULL,
    `created_by` bigint(20) NOT NULL,
    `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (`id`),
    KEY `idx_name` (`name`),
    KEY `idx_ip_address` (`ip_address`),
    KEY `idx_device_type` (`device_type`),
    KEY `idx_protocol_type` (`protocol_type`),
    KEY `idx_status` (`status`),
    KEY `idx_group_id` (`group_id`),
    KEY `idx_created_by` (`created_by`),
    FOREIGN KEY (`group_id`) REFERENCES `device_groups` (`id`) ON DELETE SET NULL,
    FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 服务区表
CREATE TABLE `service_zones` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT,
    `name` varchar(100) NOT NULL,
    `description` text,
    `ssh_host` varchar(45) NOT NULL,
    `ssh_port` int(11) NOT NULL DEFAULT 22,
    `ssh_username` varchar(100) NOT NULL,
    `ssh_password` varchar(255) DEFAULT NULL,
    `ssh_private_key` text DEFAULT NULL,
    `status` enum('online', 'offline', 'unknown') DEFAULT 'unknown',
    `last_heartbeat` datetime(6) NULL,
    `cpu_usage` decimal(5,2) DEFAULT NULL,
    `memory_usage` decimal(5,2) DEFAULT NULL,
    `disk_usage` decimal(5,2) DEFAULT NULL,
    `created_by` bigint(20) NOT NULL,
    `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (`id`),
    KEY `idx_name` (`name`),
    KEY `idx_ssh_host` (`ssh_host`),
    KEY `idx_status` (`status`),
    KEY `idx_created_by` (`created_by`),
    FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 采集器表
CREATE TABLE `collectors` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT,
    `name` varchar(100) NOT NULL,
    `collector_type` varchar(50) NOT NULL,
    `protocol_types` json NOT NULL,
    `host` varchar(45) NOT NULL,
    `port` int(11) NOT NULL,
    `version` varchar(50) DEFAULT NULL,
    `status` enum('online', 'offline', 'busy', 'error') DEFAULT 'offline',
    `last_heartbeat` datetime(6) NULL,
    `cpu_usage` decimal(5,2) DEFAULT NULL,
    `memory_usage` decimal(5,2) DEFAULT NULL,
    `active_tasks` int(11) DEFAULT 0,
    `max_concurrent_tasks` int(11) DEFAULT 10,
    `service_zone_id` bigint(20) NULL,
    `tags` json DEFAULT NULL,
    `config` json DEFAULT NULL,
    `registered_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (`id`),
    KEY `idx_name` (`name`),
    KEY `idx_collector_type` (`collector_type`),
    KEY `idx_host_port` (`host`, `port`),
    KEY `idx_status` (`status`),
    KEY `idx_service_zone_id` (`service_zone_id`),
    FOREIGN KEY (`service_zone_id`) REFERENCES `service_zones` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 任务模板表
CREATE TABLE `task_templates` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT,
    `name` varchar(100) NOT NULL,
    `description` text,
    `protocol_type` enum('SSH', 'SNMP', 'API', 'TELNET') NOT NULL,
    `command_template` text NOT NULL,
    `timeout` int(11) DEFAULT 30,
    `retry_count` int(11) DEFAULT 3,
    `parser_type` varchar(50) DEFAULT NULL,
    `parser_config` json DEFAULT NULL,
    `created_by` bigint(20) NOT NULL,
    `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (`id`),
    KEY `idx_name` (`name`),
    KEY `idx_protocol_type` (`protocol_type`),
    KEY `idx_created_by` (`created_by`),
    FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 采集任务表
CREATE TABLE `collection_tasks` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT,
    `name` varchar(100) NOT NULL,
    `description` text,
    `device_id` bigint(20) NOT NULL,
    `template_id` bigint(20) NULL,
    `command` text NOT NULL,
    `cron_expression` varchar(100) DEFAULT NULL,
    `timeout` int(11) DEFAULT 30,
    `retry_count` int(11) DEFAULT 3,
    `status` enum('active', 'inactive', 'paused') DEFAULT 'active',
    `last_execution_time` datetime(6) NULL,
    `next_execution_time` datetime(6) NULL,
    `execution_count` int(11) DEFAULT 0,
    `success_count` int(11) DEFAULT 0,
    `failure_count` int(11) DEFAULT 0,
    `xxl_job_id` int(11) NULL,
    `created_by` bigint(20) NOT NULL,
    `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (`id`),
    KEY `idx_name` (`name`),
    KEY `idx_device_id` (`device_id`),
    KEY `idx_template_id` (`template_id`),
    KEY `idx_status` (`status`),
    KEY `idx_next_execution_time` (`next_execution_time`),
    KEY `idx_created_by` (`created_by`),
    FOREIGN KEY (`device_id`) REFERENCES `devices` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`template_id`) REFERENCES `task_templates` (`id`) ON DELETE SET NULL,
    FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 任务执行记录表
CREATE TABLE `task_executions` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT,
    `task_id` bigint(20) NOT NULL,
    `collector_id` bigint(20) NULL,
    `execution_id` varchar(100) NOT NULL,
    `status` enum('pending', 'running', 'success', 'failed', 'timeout', 'cancelled') DEFAULT 'pending',
    `start_time` datetime(6) NULL,
    `end_time` datetime(6) NULL,
    `duration` int(11) NULL,
    `command` text NOT NULL,
    `result_data` longtext DEFAULT NULL,
    `error_message` text DEFAULT NULL,
    `retry_count` int(11) DEFAULT 0,
    `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (`id`),
    KEY `idx_task_id` (`task_id`),
    KEY `idx_collector_id` (`collector_id`),
    KEY `idx_execution_id` (`execution_id`),
    KEY `idx_status` (`status`),
    KEY `idx_start_time` (`start_time`),
    KEY `idx_created_at` (`created_at`),
    FOREIGN KEY (`task_id`) REFERENCES `collection_tasks` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`collector_id`) REFERENCES `collectors` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 采集结果表
CREATE TABLE `collection_results` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT,
    `execution_id` bigint(20) NOT NULL,
    `device_id` bigint(20) NOT NULL,
    `task_id` bigint(20) NOT NULL,
    `raw_data` longtext NOT NULL,
    `parsed_data` json DEFAULT NULL,
    `metrics` json DEFAULT NULL,
    `status` enum('normal', 'warning', 'error') DEFAULT 'normal',
    `collected_at` datetime(6) NOT NULL,
    `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (`id`),
    KEY `idx_execution_id` (`execution_id`),
    KEY `idx_device_id` (`device_id`),
    KEY `idx_task_id` (`task_id`),
    KEY `idx_status` (`status`),
    KEY `idx_collected_at` (`collected_at`),
    KEY `idx_created_at` (`created_at`),
    FOREIGN KEY (`execution_id`) REFERENCES `task_executions` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`device_id`) REFERENCES `devices` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`task_id`) REFERENCES `collection_tasks` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 告警规则表
CREATE TABLE `alert_rules` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT,
    `name` varchar(100) NOT NULL,
    `description` text,
    `rule_type` enum('threshold', 'pattern', 'anomaly') NOT NULL,
    `conditions` json NOT NULL,
    `severity` enum('low', 'medium', 'high', 'critical') DEFAULT 'medium',
    `notification_channels` json DEFAULT NULL,
    `is_active` tinyint(1) DEFAULT 1,
    `created_by` bigint(20) NOT NULL,
    `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (`id`),
    KEY `idx_name` (`name`),
    KEY `idx_rule_type` (`rule_type`),
    KEY `idx_severity` (`severity`),
    KEY `idx_is_active` (`is_active`),
    KEY `idx_created_by` (`created_by`),
    FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 告警记录表
CREATE TABLE `alerts` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT,
    `rule_id` bigint(20) NOT NULL,
    `device_id` bigint(20) NULL,
    `task_id` bigint(20) NULL,
    `execution_id` bigint(20) NULL,
    `title` varchar(200) NOT NULL,
    `message` text NOT NULL,
    `severity` enum('low', 'medium', 'high', 'critical') NOT NULL,
    `status` enum('open', 'acknowledged', 'resolved', 'closed') DEFAULT 'open',
    `triggered_at` datetime(6) NOT NULL,
    `acknowledged_at` datetime(6) NULL,
    `acknowledged_by` bigint(20) NULL,
    `resolved_at` datetime(6) NULL,
    `resolved_by` bigint(20) NULL,
    `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (`id`),
    KEY `idx_rule_id` (`rule_id`),
    KEY `idx_device_id` (`device_id`),
    KEY `idx_task_id` (`task_id`),
    KEY `idx_execution_id` (`execution_id`),
    KEY `idx_severity` (`severity`),
    KEY `idx_status` (`status`),
    KEY `idx_triggered_at` (`triggered_at`),
    KEY `idx_acknowledged_by` (`acknowledged_by`),
    KEY `idx_resolved_by` (`resolved_by`),
    FOREIGN KEY (`rule_id`) REFERENCES `alert_rules` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`device_id`) REFERENCES `devices` (`id`) ON DELETE SET NULL,
    FOREIGN KEY (`task_id`) REFERENCES `collection_tasks` (`id`) ON DELETE SET NULL,
    FOREIGN KEY (`execution_id`) REFERENCES `task_executions` (`id`) ON DELETE SET NULL,
    FOREIGN KEY (`acknowledged_by`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    FOREIGN KEY (`resolved_by`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 操作日志表
CREATE TABLE `operation_logs` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT,
    `user_id` bigint(20) NOT NULL,
    `action` varchar(100) NOT NULL,
    `resource_type` varchar(50) NOT NULL,
    `resource_id` varchar(100) DEFAULT NULL,
    `description` text,
    `ip_address` varchar(45) DEFAULT NULL,
    `user_agent` varchar(500) DEFAULT NULL,
    `request_data` json DEFAULT NULL,
    `response_data` json DEFAULT NULL,
    `status` enum('success', 'failed') DEFAULT 'success',
    `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (`id`),
    KEY `idx_user_id` (`user_id`),
    KEY `idx_action` (`action`),
    KEY `idx_resource_type` (`resource_type`),
    KEY `idx_status` (`status`),
    KEY `idx_created_at` (`created_at`),
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 系统配置表
CREATE TABLE `system_configs` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT,
    `key` varchar(100) NOT NULL UNIQUE,
    `value` text NOT NULL,
    `description` text,
    `config_type` enum('string', 'number', 'boolean', 'json') DEFAULT 'string',
    `is_encrypted` tinyint(1) DEFAULT 0,
    `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (`id`),
    KEY `idx_key` (`key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 插入默认数据
INSERT INTO `roles` (`name`, `description`, `permissions`) VALUES
('admin', '系统管理员', '["*"]'),
('operator', '操作员', '["device:read", "device:write", "task:read", "task:write", "result:read"]'),
('viewer', '查看者', '["device:read", "task:read", "result:read"]');

INSERT INTO `system_configs` (`key`, `value`, `description`, `config_type`) VALUES
('system.name', '多协议采集控制器', '系统名称', 'string'),
('system.version', '1.0.0', '系统版本', 'string'),
('task.default_timeout', '30', '默认任务超时时间(秒)', 'number'),
('task.default_retry_count', '3', '默认重试次数', 'number'),
('collector.heartbeat_interval', '30', '采集器心跳间隔(秒)', 'number'),
('alert.email_enabled', 'false', '是否启用邮件告警', 'boolean'),
('alert.dingtalk_enabled', 'false', '是否启用钉钉告警', 'boolean');