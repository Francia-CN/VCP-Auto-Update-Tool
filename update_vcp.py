#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VCP 自动更新脚本 v1.0
功能：
1. 从原作者分支获取最新代码并合并到本地
2. 自动解决冲突（以原作者版本为准）
3. 推送到自己的远程分支
4. 重新部署 VCPToolBox Docker 应用
5. 提供详细的日志记录和错误处理
6. 支持 Git 回滚功能
7. 配置文件支持
8. Docker健康检查
9. 所有运行时文件保存在 VCPUpdate 目录下
"""

import os
import sys
import subprocess
import logging
import datetime
import json
import shutil
import time
import threading
import configparser
import argparse
import socket
import shlex
from typing import Dict, List, Optional, Tuple, Union, Any
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict, field
from enum import Enum
from collections import defaultdict
import traceback
import hashlib
import re
import tempfile

# 版本信息
__version__ = "v1.0"
__author__ = "VCP Auto Updater"

# 全局锁，用于处理共享资源的并发访问
_global_git_lock = threading.Lock()
_global_docker_lock = threading.Lock()

class UpdateStatus(Enum):
    """更新状态枚举"""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    SKIPPED = "skipped"
    NO_CHANGES = "no_changes"
    IN_PROGRESS = "in_progress"
    CANCELLED = "cancelled"

class GitCheckpointType(Enum):
    """Git检查点类型"""
    BEFORE_UPDATE = "before_update"
    AFTER_REMOTE_SETUP = "after_remote_setup"
    AFTER_FETCH = "after_fetch"
    AFTER_MERGE = "after_merge"
    AFTER_PUSH = "after_push"
    MANUAL = "manual"
    AUTO_BACKUP = "auto_backup"

@dataclass
class ProjectConfig:
    """项目配置数据类"""
    path: Path
    upstream_url: str
    origin_url: str
    has_docker: bool = False
    docker_compose_file: str = "docker-compose.yml"
    is_git_repo: bool = True
    docker_health_check_timeout: int = 60
    docker_health_check_interval: int = 5
    docker_port: Optional[int] = None
    docker_service_name: Optional[str] = None
    branch: str = "main"
    auto_stash: bool = True
    custom_commands: List[str] = field(default_factory=list)
    
@dataclass
class UpdateResult:
    """更新结果数据类"""
    project_name: str
    status: UpdateStatus
    git_status: Optional[UpdateStatus] = None
    docker_status: Optional[UpdateStatus] = None
    start_time: Optional[datetime.datetime] = None
    end_time: Optional[datetime.datetime] = None
    error_message: Optional[str] = None
    changes_count: int = 0
    files_changed: List[str] = field(default_factory=list)
    backup_branch: Optional[str] = None
    stash_ref: Optional[str] = None
    
    @property
    def duration(self) -> Optional[float]:
        """计算耗时"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

class VCPAutoUpdater:
    """VCP自动更新器主类"""
    
    def __init__(self, vcp_root_path: str = None, vcpupdate_path: str = None, config_file: str = None):
        """初始化自动更新器"""
        # 设置路径
        self.script_path = Path(__file__).resolve()
        self.vcpupdate_path = Path(vcpupdate_path) if vcpupdate_path else self.script_path.parent
        self.vcp_root = Path(vcp_root_path) if vcp_root_path else self.vcpupdate_path.parent
        
        # 确保VCPUpdate目录存在
        self.vcpupdate_path.mkdir(exist_ok=True)
        
        # 配置文件路径（在VCPUpdate目录下）
        self.config_file = Path(config_file) if config_file else self.vcpupdate_path / "update_vcp_config.ini"
        
        # 初始化锁和状态（必须在任何可能调用日志的方法之前）
        self.log_lock = threading.Lock()
        self.data_lock = threading.Lock()
        self.is_running = False
        self.should_cancel = False
        self.shutdown_event = threading.Event()
        
        # 初始化统计和结果（在加载配置前，避免被覆盖）
        with self.data_lock:
            self.update_stats = defaultdict(int)
            self.update_results: List[UpdateResult] = []
            self.rollback_info = {}
            self.git_checkpoints = {}
        
        # 加载配置
        self.config = self._load_config()
        
        # 初始化Docker命令
        self.docker_compose_cmd = self._detect_docker_compose_command()
        
        # 智能检测项目路径
        self.vcpchat_path = self._detect_project_path("VCPChat")
        self.vcptoolbox_path = self._detect_project_path("VCPToolBox")
        
        # 项目配置
        self.projects = self._detect_projects()
        if not self.projects:
            self._initialize_default_projects()
        
        # 设置日志
        self.logger = None
        self.setup_logging()
        
        # 验证配置
        self._validate_config()
        
        # 文件路径（都在VCPUpdate目录下）
        self.rollback_info_file = self.vcpupdate_path / "update_vcp_rollback_info.json"
        self.cache_dir = self.vcpupdate_path / "__pycache__"
        self.backup_dir = self.vcpupdate_path / "backups"
        
        # 创建必要的目录
        self.cache_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)
        
        # 加载历史数据（仅在初始化时）
        self._load_historical_data()
        
        # 执行初始检查
        self._initial_check()
        
        # 性能优化配置
        self.max_workers = self.config.getint('performance', 'max_workers', 
                                            fallback=min(len(self.projects), 4))
        self.git_timeout = self.config.getint('timeouts', 'git_timeout', fallback=180)
        self.docker_timeout = self.config.getint('timeouts', 'docker_timeout', fallback=900)
        
        # 项目别名映射
        self.project_aliases = {
            'chat': ['vcpchat', 'chat'],
            'vcpchat': ['vcpchat', 'chat'],
            'toolbox': ['vcptoolbox', 'toolbox', 'tb'],
            'tb': ['vcptoolbox', 'toolbox', 'tb'],
            'vcptoolbox': ['vcptoolbox', 'toolbox', 'tb']
        }

    def _load_historical_data(self):
        """加载历史数据（仅在初始化时调用）"""
        try:
            if self.rollback_info_file.exists():
                with open(self.rollback_info_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                if isinstance(data, dict):
                    with self.data_lock:
                        self.rollback_info = data.get("rollback_info", {})
                        self.git_checkpoints = data.get("git_checkpoints", {})
                        
                        # 只在初始化时加载历史统计（用于显示）
                        historical_stats = data.get("update_stats", {})
                        # 不直接覆盖current stats，保存为历史记录
                        self._historical_stats = historical_stats
                        
                        # 加载历史结果记录
                        results_data = data.get("update_results", [])
                        for result_dict in results_data[-5:]:  # 只保留最近5条历史记录
                            try:
                                # 转换时间戳和状态
                                if result_dict.get('start_time'):
                                    result_dict['start_time'] = datetime.datetime.fromisoformat(result_dict['start_time'])
                                if result_dict.get('end_time'):
                                    result_dict['end_time'] = datetime.datetime.fromisoformat(result_dict['end_time'])
                                if result_dict.get('status'):
                                    result_dict['status'] = UpdateStatus(result_dict['status'])
                                if result_dict.get('git_status'):
                                    result_dict['git_status'] = UpdateStatus(result_dict['git_status'])
                                if result_dict.get('docker_status'):
                                    result_dict['docker_status'] = UpdateStatus(result_dict['docker_status'])
                                
                                self.update_results.append(UpdateResult(**result_dict))
                            except Exception as e:
                                self._log_safe("debug", f"跳过无效的历史记录: {str(e)}")
                                continue
                            
                self._log_safe("debug", "已加载历史数据")
        except Exception as e:
            self._log_safe("warning", f"加载历史数据失败: {str(e)}")
            with self.data_lock:
                self.rollback_info = {}
                self.git_checkpoints = {}
                self._historical_stats = {}
        
    def _log_safe(self, level: str, message: str, exc_info: bool = False):
        """线程安全的日志记录"""
        try:
            if self.logger:
                with self.log_lock:
                    getattr(self.logger, level.lower())(message, exc_info=exc_info)
            else:
                print(f"[{level.upper()}] {message}")
                if exc_info:
                    traceback.print_exc()
        except Exception as e:
            # 避免日志系统本身出错导致程序崩溃
            print(f"[LOGGING_ERROR] 日志记录失败: {str(e)} | 原消息: [{level.upper()}] {message}")
            if exc_info:
                traceback.print_exc()
        
    def _validate_config(self):
        """验证配置文件内容"""
        # 检查origin URLs是否已配置 - 使用动态检测而非硬编码
        project_base_names = set()
        for project_name in self.projects.keys():
            # 提取基础项目名称（去除-main等后缀）
            base_name = project_name.split('-')[0]
            if base_name in ['VCPChat', 'VCPToolBox']:
                project_base_names.add(base_name)
        
        missing_origins = []
        for project_name in project_base_names:
            origin_url = self._get_origin_url_from_config(project_name, "")
            if not origin_url or origin_url == f"https://github.com/YOUR_USERNAME/{project_name}.git":
                missing_origins.append(project_name)
                self._log_safe("warning", f"请在配置文件[origins]部分设置{project_name}的Fork仓库URL")
                self._log_safe("warning", f"示例: {project_name} = https://github.com/YOUR_USERNAME/{project_name}.git")

        if missing_origins:
            self._log_safe("warning", f"未配置Fork仓库URL的项目: {', '.join(missing_origins)}")
            self._log_safe("warning", "这些项目将跳过推送到远程仓库的步骤")
            
            # 如果推送是必需的，将缺失origin URL视为硬错误
            if self.config.getboolean('general', 'require_origin_url', fallback=False):
                raise ValueError(f"必需配置Fork仓库URL但缺失: {', '.join(missing_origins)}")

        # 验证超时值范围
        timeouts = ['git_timeout', 'docker_timeout', 'docker_health_check_timeout']
        for timeout_key in timeouts:
            timeout_value = self.config.getint('timeouts', timeout_key, fallback=0)
            if timeout_value < 10 or timeout_value > 3600:
                self._log_safe("warning", f"超时配置 {timeout_key}={timeout_value} 可能不合理 (建议: 10-3600秒)")
                
        # 验证自定义命令安全性
        self._validate_custom_commands()
    
    def _validate_custom_commands(self):
        """验证自定义命令的安全性"""
        if not self.config.has_section('custom_commands'):
            return
            
        # 危险命令列表
        dangerous_patterns = [
            r'rm\s+-rf',
            r'sudo\s+',
            r'chmod\s+777',
            r'>/dev/null',
            r'\|\s*sh',
            r'eval\s+',
            r'exec\s+',
            r'&&\s*rm',
            r';\s*rm',
            r'curl.*\|\s*sh'
        ]
        
        for project_name in self.config.options('custom_commands'):
            commands = self.config.get('custom_commands', project_name, fallback='')
            if commands:
                for pattern in dangerous_patterns:
                    if re.search(pattern, commands, re.IGNORECASE):
                        self._log_safe("error", f"检测到危险的自定义命令模式: {pattern} in {project_name}")
                        raise ValueError(f"自定义命令包含危险模式: {pattern}")
    
    def _load_config(self) -> configparser.ConfigParser:
        """加载配置文件"""
        config = configparser.ConfigParser()
        
        # 默认配置
        config['general'] = {
            'auto_merge_conflicts': 'true',
            'force_push': 'false',
            'backup_before_update': 'true',
            'verify_docker_health': 'true',
            'skip_unchanged_docker': 'true',
            'create_restore_points': 'true',
            'max_backup_age_days': '30',
            'auto_cleanup': 'true',
            'push_checkpoints': 'false',
            'require_origin_url': 'false',
            'interactive_mode': 'false',
            'safe_merge_only': 'false'
        }
        
        config['timeouts'] = {
            'git_timeout': '180',
            'docker_timeout': '900',
            'docker_health_check_timeout': '60',
            'docker_health_check_interval': '5',
            'network_retry_count': '3',
            'network_retry_delay': '5'
        }
        
        config['docker'] = {
            'auto_prune': 'false',  # 改为false以避免删除无关资源
            'restart_policy': 'unless-stopped',
            'max_restart_attempts': '3',
            'use_simple_health_check': 'true',
            'wait_before_health_check': '10',
            'rebuild_on_config_change': 'true',
            'remove_orphans': 'true',
            'prune_scope': 'project'  # 限制清理范围
        }
        
        config['performance'] = {
            'max_workers': '4',
            'enable_parallel_git': 'true',
            'enable_parallel_docker': 'false',
            'batch_size': '10'
        }
        
        config['logging'] = {
            'log_level': 'INFO',
            'max_log_files': '30',
            'log_rotation_size_mb': '10',
            'enable_debug_logging': 'false'
        }
        
        config['network'] = {
            'use_proxy': 'false',
            'http_proxy': '',
            'https_proxy': '',
            'no_proxy': 'localhost,127.0.0.1',
            'ssl_verify': 'true'
        }
        
        config['projects'] = {}
        config['origins'] = {}
        config['custom_commands'] = {}
        
        # 如果配置文件存在，加载它
        if self.config_file.exists():
            try:
                config.read(self.config_file, encoding='utf-8')
            except Exception as e:
                print(f"警告: 配置文件加载失败: {e}")
                print("将使用默认配置")
        else:
            # 创建默认配置文件
            self._create_default_config(config)
        
        return config
    
    def _create_default_config(self, config: configparser.ConfigParser):
        """创建默认配置文件 - 修复版本"""
        try:
            # 确保目录存在
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 完全手动生成配置内容，避免重复section的问题
            config_content = f"""# VCP Auto Update Configuration File
# Version: {__version__}
# Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
#
# 配置说明：
# - true/false: 布尔值
# - 数字: 整数或浮点数
# - 字符串: 文本值
# - 留空: 使用默认值
#
# 重要：请在 [origins] 部分设置您的Fork仓库URL

[general]
auto_merge_conflicts = true
force_push = false
backup_before_update = true
verify_docker_health = true
skip_unchanged_docker = true
create_restore_points = true
max_backup_age_days = 30
auto_cleanup = true
push_checkpoints = false
require_origin_url = false
interactive_mode = false
safe_merge_only = false

[timeouts]
git_timeout = 180
docker_timeout = 900
docker_health_check_timeout = 60
docker_health_check_interval = 5
network_retry_count = 3
network_retry_delay = 5

[docker]
auto_prune = false
restart_policy = unless-stopped
max_restart_attempts = 3
use_simple_health_check = true
wait_before_health_check = 10
rebuild_on_config_change = true
remove_orphans = true
prune_scope = project

[performance]
max_workers = 4
enable_parallel_git = true
enable_parallel_docker = false
batch_size = 10

[logging]
log_level = INFO
max_log_files = 30
log_rotation_size_mb = 10
enable_debug_logging = false

[network]
use_proxy = false
http_proxy = 
https_proxy = 
no_proxy = localhost,127.0.0.1
ssl_verify = true

[projects]

[origins]
VCPChat = https://github.com/YOUR_USERNAME/VCPChat.git
VCPToolBox = https://github.com/YOUR_USERNAME/VCPToolBox.git

[custom_commands]

"""
            
            # 直接写入文件，不使用config.write()以避免重复section
            with open(self.config_file, 'w', encoding='utf-8') as f:
                f.write(config_content)
            
            print(f"已创建默认配置文件: {self.config_file}")
        except Exception as e:
            print(f"创建配置文件失败: {str(e)}")
    
    def _detect_docker_compose_command(self) -> List[str]:
        """检测可用的docker-compose命令"""
        # 优先检查新版docker compose命令
        commands_to_check = [
            (["docker", "compose", "version"], ["docker", "compose"]),
            (["docker-compose", "version"], ["docker-compose"]),
            (["podman-compose", "version"], ["podman-compose"])
        ]
        
        for check_cmd, use_cmd in commands_to_check:
            try:
                result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return use_cmd
            except:
                continue
        
        # 默认使用新版
        return ["docker", "compose"]
    
    def _detect_project_path(self, project_name: str) -> Path:
        """智能检测项目路径"""
        # 项目可能的名称变体
        possible_names = [
            f"{project_name}-main",
            project_name,
            f"{project_name.lower()}-main", 
            project_name.lower(),
            f"{project_name}-master",
            f"{project_name.lower()}-master",
            f"{project_name}-dev",
            f"{project_name.lower()}-dev"
        ]
        
        # 首先查找Git仓库
        for name in possible_names:
            path = self.vcp_root / name
            if path.exists() and (path / ".git").exists():
                return path
        
        # 如果没有Git仓库，查找目录
        for name in possible_names:
            path = self.vcp_root / name
            if path.exists() and path.is_dir():
                return path
                
        # 返回默认路径
        return self.vcp_root / f"{project_name}-main"
    
    def _detect_projects(self) -> Dict[str, ProjectConfig]:
        """自动检测现有项目"""
        projects = {}
        
        # 从配置文件读取项目设置
        if self.config.has_section('projects'):
            for project_name in self.config.options('projects'):
                try:
                    project_data = json.loads(self.config.get('projects', project_name))
                    project_path = Path(project_data.get('path', ''))
                    
                    # 如果路径是相对路径，转换为绝对路径
                    if not project_path.is_absolute():
                        project_path = self.vcp_root / project_path
                    
                    if project_path.exists():
                        project_data['path'] = project_path
                        projects[project_name] = ProjectConfig(**project_data)
                except (json.JSONDecodeError, TypeError, ValueError) as e:
                    self._log_safe("error", f"加载项目配置失败 {project_name}: {str(e)}")
                    continue
        
        # 自动检测VCPChat
        if self.vcpchat_path.exists() and self.vcpchat_path.name not in projects:
            is_git_repo = (self.vcpchat_path / ".git").exists()
            projects[self.vcpchat_path.name] = ProjectConfig(
                path=self.vcpchat_path,
                upstream_url=self._get_upstream_url_from_config("VCPChat", "https://github.com/lioensky/VCPChat.git"),
                origin_url=self._get_origin_url_from_config("VCPChat", ""),
                has_docker=False,
                is_git_repo=is_git_repo
            ) 
        
        # 自动检测VCPToolBox  
        if self.vcptoolbox_path.exists() and self.vcptoolbox_path.name not in projects:
            is_git_repo = (self.vcptoolbox_path / ".git").exists()
            docker_compose_file = self._find_docker_compose_file(self.vcptoolbox_path)
            has_docker = bool(docker_compose_file)
            
            projects[self.vcptoolbox_path.name] = ProjectConfig(
                path=self.vcptoolbox_path,
                upstream_url=self._get_upstream_url_from_config("VCPToolBox", "https://github.com/lioensky/VCPToolBox.git"),
                origin_url=self._get_origin_url_from_config("VCPToolBox", ""),
                has_docker=has_docker,
                docker_compose_file=docker_compose_file or "docker-compose.yml",
                is_git_repo=is_git_repo,
                docker_health_check_timeout=self.config.getint('timeouts', 'docker_health_check_timeout', fallback=60),
                docker_port=3210,
                docker_service_name="vcptoolbox"
            )
        
        return projects
    
    def _get_origin_url_from_config(self, project_name: str, default: str) -> str:
        """从配置文件获取origin URL"""
        if self.config.has_option('origins', project_name):
            return self.config.get('origins', project_name)
        return default
    
    def _get_upstream_url_from_config(self, project_name: str, default: str) -> str:
       """从配置文件获取upstream URL"""
       if self.config.has_option('upstreams', project_name):
        return self.config.get('upstreams', project_name)
       return default

    def _find_docker_compose_file(self, project_path: Path) -> Optional[str]:
        """查找Docker Compose文件"""
        possible_files = [
            "docker-compose.yml",
            "docker-compose.yaml", 
            "compose.yml",
            "compose.yaml",
            "docker-compose.prod.yml",
            "docker-compose.production.yml"
        ]
        
        for file_name in possible_files:
            if (project_path / file_name).exists():
                return file_name
        
        return None
    
    def _initialize_default_projects(self):
        """初始化默认项目配置"""
        self.projects = {
            "VCPChat-main": ProjectConfig(
                path=self.vcpchat_path,
                upstream_url="https://github.com/lioensky/VCPChat.git",
                origin_url=self._get_origin_url_from_config("VCPChat", ""),
                has_docker=False
            ),
            "VCPToolBox-main": ProjectConfig(
                path=self.vcptoolbox_path,
                upstream_url="https://github.com/lioensky/VCPToolBox.git",
                origin_url=self._get_origin_url_from_config("VCPToolBox", ""),
                has_docker=True,
                docker_compose_file="docker-compose.yml",
                docker_port=3210,
                docker_service_name="vcptoolbox"
            )
        }
    
    def setup_logging(self):
        """设置日志配置"""
        # 日志目录在VCPUpdate下
        log_dir = self.vcpupdate_path / "update_vcp_logs"
        log_dir.mkdir(exist_ok=True)
        
        # 清理旧日志
        self._cleanup_old_logs(log_dir)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"update_vcp_{timestamp}.log"
        
        # 获取日志级别
        log_level_str = self.config.get('logging', 'log_level', fallback='INFO')
        log_level = getattr(logging, log_level_str.upper(), logging.INFO)
        
        # 配置日志格式
        log_format = '%(asctime)s [%(levelname)s] [%(funcName)s] %(message)s'
        date_format = '%Y-%m-%d %H:%M:%S'
        
        # 创建日志处理器
        handlers = [
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
        
        # 配置根日志记录器
        logging.basicConfig(
            level=log_level,
            format=log_format,
            datefmt=date_format,
            handlers=handlers,
            force=True  # 强制重新配置
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"=" * 60)
        self.logger.info(f"VCP 自动更新工具 {__version__}")
        self.logger.info(f"开始时间: {datetime.datetime.now()}")
        self.logger.info(f"日志文件: {log_file}")
        self.logger.info(f"配置文件: {self.config_file}")
        self.logger.info(f"VCP根目录: {self.vcp_root}")
        self.logger.info(f"VCPUpdate目录: {self.vcpupdate_path}")
        self.logger.info(f"=" * 60)
    
    def _cleanup_old_logs(self, log_dir: Path):
        """清理旧日志文件"""
        try:
            max_files = self.config.getint('logging', 'max_log_files', fallback=30)
            max_age_days = self.config.getint('general', 'max_backup_age_days', fallback=30)
            
            # 获取所有日志文件
            log_files = list(log_dir.glob("update_vcp_*.log"))
            
            # 按修改时间排序
            log_files.sort(key=lambda x: x.stat().st_mtime)
            
            # 删除超过数量限制的文件
            if len(log_files) > max_files:
                for log_file in log_files[:-max_files]:
                    log_file.unlink()
                    
            # 删除超过时间限制的文件
            cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
            for log_file in log_files:
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    
        except Exception as e:
            self._log_safe("warning", f"清理旧日志失败: {str(e)}")
    
    def _initial_check(self):
        """执行初始检查"""
        self._log_safe("info", "执行环境和项目初始检查...")
        
        # 检查Python具体版本和功能
        if sys.version_info < (3, 7):
            self._log_safe("error", f"Python版本过低: {sys.version}")
            self._log_safe("error", "需要Python 3.7或更高版本")
            sys.exit(1)
        
        # 检查VCP根目录
        if not self.vcp_root.exists():
            self._log_safe("error", f"VCP根目录不存在: {self.vcp_root}")
            return False
            
        # 检查项目目录结构
        detected_projects = []
        warnings = []
        
        for project_name, config in self.projects.items():
            if config.path.exists():
                if config.is_git_repo and (config.path / ".git").exists():
                    detected_projects.append(f"{project_name} ({config.path})")
                elif config.is_git_repo:
                    warnings.append(f"{project_name}目录存在但不是Git仓库: {config.path}")
                else:
                    detected_projects.append(f"{project_name} ({config.path}) [非Git项目]")
            else:
                warnings.append(f"{project_name}目录不存在: {config.path}")
        
        # 检查Git
        git_available = self.check_git_availability()
        if not git_available:
            self._log_safe("error", "Git不可用，请确保Git已安装并在PATH中")
            return False
        
        # 检查Docker
        docker_available = self.check_docker_availability()
        if docker_available:
            self._log_safe("info", "Docker服务可用")
        else:
            self._log_safe("warning", "Docker服务不可用，将跳过Docker相关操作")
        
        # 输出检测结果
        if detected_projects:
            self._log_safe("info", f"检测到项目: {', '.join(detected_projects)}")
        else:
            self._log_safe("warning", "未检测到有效的VCP项目")
            
        for warning in warnings:
            self._log_safe("warning", warning)
            
        # 检查网络配置
        if self.config.getboolean('network', 'use_proxy', fallback=False):
            self._log_safe("info", "检测到代理配置")
            self._setup_proxy_environment()
            
        return True
    
    def check_git_availability(self) -> bool:
        """检查Git是否可用"""
        try:
            result = subprocess.run(["git", "--version"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                git_version = result.stdout.strip()
                self._log_safe("info", f"Git版本: {git_version}")
                return True
        except Exception as e:
            self._log_safe("error", f"检查Git时发生异常: {str(e)}")
        return False
    
    def check_docker_availability(self) -> bool:
        """检查Docker是否可用"""
        try:
            # 检查Docker是否运行
            result = subprocess.run(["docker", "version"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                return False
            
            # 检查docker compose命令
            result = subprocess.run(self.docker_compose_cmd + ["version"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                return False
            
            return True
            
        except Exception:
            return False
    
    def _setup_proxy_environment(self):
        """设置代理环境变量"""
        http_proxy = self.config.get('network', 'http_proxy', fallback='')
        https_proxy = self.config.get('network', 'https_proxy', fallback='')
        no_proxy = self.config.get('network', 'no_proxy', fallback='')
        
        if http_proxy:
            os.environ['HTTP_PROXY'] = http_proxy
            os.environ['http_proxy'] = http_proxy
            self._log_safe("info", f"设置HTTP代理: {http_proxy}")
            
        if https_proxy:
            os.environ['HTTPS_PROXY'] = https_proxy
            os.environ['https_proxy'] = https_proxy
            self._log_safe("info", f"设置HTTPS代理: {https_proxy}")
            
        if no_proxy:
            os.environ['NO_PROXY'] = no_proxy
            os.environ['no_proxy'] = no_proxy
    
    def safe_log(self, level: str, message: str, project_name: str = ""):
        """线程安全的日志记录"""
        if project_name:
            formatted_message = f"[{project_name}] {message}"
        else:
            formatted_message = message
        self._log_safe(level, formatted_message)
    
    def run_command(self, command: List[str], cwd: Path = None, 
                   capture_output: bool = True, timeout: int = None,
                   retry_on_failure: bool = None) -> Tuple[bool, str, str]:
        """执行命令并返回结果"""
        cwd = cwd or self.vcp_root
        timeout = timeout or (self.docker_timeout if 'docker' in ' '.join(command) else self.git_timeout)
        
        # 对网络相关命令默认启用重试
        if retry_on_failure is None:
            network_commands = ['fetch', 'push', 'pull', 'clone']
            retry_on_failure = any(cmd in ' '.join(command) for cmd in network_commands)
        
        # 添加重试逻辑
        max_retries = self.config.getint('timeouts', 'network_retry_count', fallback=3) if retry_on_failure else 1
        retry_delay = self.config.getint('timeouts', 'network_retry_delay', fallback=5)
        
        for attempt in range(max_retries):
            if self.shutdown_event.is_set():
                return False, "", "操作已取消"
                
            if attempt > 0:
                self._log_safe("info", f"重试命令 (尝试 {attempt + 1}/{max_retries})...")
                time.sleep(retry_delay)
            
            self._log_safe("info", f"执行命令: {' '.join(command)} (工作目录: {cwd})")
            
            try:
                # Windows路径处理
                cwd_str = str(Path(cwd).resolve())

                process_kwargs = {
                    "cwd": cwd_str,
                    "text": True,
                    "encoding": 'utf-8',
                    "timeout": timeout,
                    "shell": False
                }

                if capture_output:
                    process_kwargs["capture_output"] = True
                    result = subprocess.run(command, **process_kwargs)
                    success = result.returncode == 0
                    stdout = result.stdout.strip() if result.stdout else ""
                    stderr = result.stderr.strip() if result.stderr else ""
                else:
                    result = subprocess.run(command, **process_kwargs)
                    success = result.returncode == 0
                    stdout, stderr = "", ""

                if success:
                    self._log_safe("info", f"命令执行成功")
                    if stdout and self.config.getboolean('logging', 'enable_debug_logging', fallback=False):
                        self._log_safe("debug", f"标准输出: {stdout}")
                    return True, stdout, stderr
                    
                if not retry_on_failure or attempt == max_retries - 1:
                    self._log_safe("error", f"命令执行失败 (返回码: {result.returncode})")
                    if stderr:
                        self._log_safe("error", f"错误输出: {stderr}")
                    return False, stdout, stderr
                    
            except subprocess.TimeoutExpired:
                if attempt == max_retries - 1:
                    self._log_safe("error", f"命令执行超时 ({timeout}秒)")
                    return False, "", "命令执行超时"
            except Exception as e:
                if attempt == max_retries - 1:
                    self._log_safe("error", f"命令执行异常: {str(e)}")
                    return False, "", str(e)
        
        return False, "", "所有重试都失败"
    
    def _create_backup_branch(self, project_path: Path) -> Optional[str]:
        """创建备份分支"""
        try:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_branch = f"backup-before-merge-{timestamp}"
            
            # 创建备份分支
            success, _, stderr = self.run_command([
                "git", "branch", backup_branch
            ], project_path)
            
            if success:
                self._log_safe("info", f"创建备份分支: {backup_branch}")
                return backup_branch
            else:
                self._log_safe("warning", f"创建备份分支失败: {stderr}")
                return None
        except Exception as e:
            self._log_safe("warning", f"创建备份分支时发生异常: {str(e)}")
            return None
    
    def _safe_stash_changes(self, project_path: Path) -> Optional[str]:
        """安全地暂存更改"""
        try:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            stash_message = f"VCP auto-updater stash {timestamp}"
            
            success, stdout, stderr = self.run_command([
                "git", "stash", "push", "-m", stash_message
            ], project_path)
            
            if success:
                # 获取stash引用
                stash_success, stash_list, _ = self.run_command([
                    "git", "stash", "list", "--grep", stash_message
                ], project_path)
                
                if stash_success and stash_list:
                    # 提取stash引用，如stash@{0}
                    stash_ref = stash_list.split(':')[0].strip()
                    self._log_safe("info", f"创建暂存: {stash_ref}")
                    return stash_ref
                else:
                    self._log_safe("warning", "无法获取stash引用")
                    return "stash@{0}"  # 默认引用
            else:
                self._log_safe("error", f"暂存更改失败: {stderr}")
                return None
        except Exception as e:
            self._log_safe("error", f"暂存更改时发生异常: {str(e)}")
            return None
    
    def _execute_custom_commands(self, commands: List[str], cwd: Path, phase: str):
        """安全地执行自定义命令"""
        self._log_safe("info", f"执行{phase}自定义命令...")
        for cmd in commands:
            if cmd.startswith(f"{phase}:"):
                cmd = cmd[len(f"{phase}:"):]
                try:
                    # 使用shlex.split进行安全的命令解析
                    safe_cmd = shlex.split(cmd)
                    self._log_safe("info", f"执行: {cmd}")
                    success, stdout, stderr = self.run_command(safe_cmd, cwd)
                    if not success:
                        self._log_safe("warning", f"自定义命令失败: {cmd}")
                        self._log_safe("warning", f"错误: {stderr}")
                except ValueError as e:
                    self._log_safe("error", f"自定义命令解析失败: {cmd} - {str(e)}")
    
    def update_project(self, project_name: str) -> UpdateResult:
        """更新单个项目"""
        self._log_safe("info", f"{'='*60}")
        self._log_safe("info", f"开始更新项目: {project_name}")
        self._log_safe("info", f"{'='*60}")
        
        # 创建更新结果对象
        result = UpdateResult(
            project_name=project_name,
            status=UpdateStatus.IN_PROGRESS,
            start_time=datetime.datetime.now()
        )
        
        if project_name not in self.projects:
            self._log_safe("error", f"未知项目: {project_name}")
            result.status = UpdateStatus.FAILED
            result.error_message = "项目未找到"
            result.end_time = datetime.datetime.now()
            return result
        
        project_config = self.projects[project_name]
        project_path = project_config.path
        
        # 检查项目路径
        if not project_path.exists():
            self._log_safe("error", f"项目路径不存在: {project_path}")
            result.status = UpdateStatus.FAILED
            result.error_message = "项目路径不存在"
            result.end_time = datetime.datetime.now()
            return result
        
        # 检查origin URL
        if not project_config.origin_url:
            self._log_safe("error", f"未配置Fork仓库URL，请在配置文件[origins]部分设置{project_name.split('-')[0]}的URL")
            result.status = UpdateStatus.FAILED
            result.error_message = "未配置Fork仓库URL"
            result.end_time = datetime.datetime.now()
            return result
        
        # 交互模式确认
        if self.config.getboolean('general', 'interactive_mode', fallback=False):
            if not self._confirm_update(project_name):
                result.status = UpdateStatus.CANCELLED
                result.error_message = "用户取消"
                result.end_time = datetime.datetime.now()
                return result
        
        try:
            # 记录更新开始
            with self.data_lock:
                self.rollback_info[project_name] = {
                    "update_start": datetime.datetime.now().isoformat(),
                    "status": "in_progress",
                    "version": __version__
                }
            
            # 执行前置自定义命令
            if project_config.custom_commands:
                self._execute_custom_commands(project_config.custom_commands, project_path, "pre")
            
            # Git更新流程
            git_result = self._perform_git_update(project_name, project_config, project_path, result)
            result.git_status = git_result
            
            if git_result == UpdateStatus.FAILED:
                self.rollback_info[project_name]["status"] = "git_failed"
                self.save_rollback_info()
                result.status = UpdateStatus.FAILED
                result.error_message = "Git更新失败"
                result.end_time = datetime.datetime.now()
                return result
            
            # 统计变更
            if git_result == UpdateStatus.SUCCESS:
                changes = self._get_git_changes(project_path)
                result.changes_count = len(changes)
                result.files_changed = changes[:10]  # 只记录前10个文件
            
            # 如果没有代码更新且配置跳过未更改的Docker
            if git_result == UpdateStatus.NO_CHANGES and self.config.getboolean('general', 'skip_unchanged_docker', fallback=True):
                self._log_safe("info", f"{project_name} 代码未更新，跳过Docker重建")
                self.rollback_info[project_name]["status"] = "no_changes"
                self.save_rollback_info()
                result.status = UpdateStatus.NO_CHANGES
                result.end_time = datetime.datetime.now()
                return result
            
            # Docker部署（如果需要）
            if project_config.has_docker:
                if not self.check_docker_availability():
                    self._log_safe("warning", "Docker不可用，跳过Docker部署步骤")
                    self.rollback_info[project_name]["status"] = "docker_skipped"
                    self._log_safe("info", f"✅ {project_name} Git更新完成 (Docker跳过)!")
                    result.status = UpdateStatus.PARTIAL
                    result.docker_status = UpdateStatus.SKIPPED
                else:
                    docker_success = self._perform_docker_deployment(project_name, project_path)
                    result.docker_status = UpdateStatus.SUCCESS if docker_success else UpdateStatus.FAILED
                    if not docker_success:
                        self.rollback_info[project_name]["status"] = "docker_failed"
                        self.save_rollback_info()
                        self._log_safe("warning", f"⚠️ {project_name} Git更新成功但Docker部署失败")
                        result.status = UpdateStatus.PARTIAL
                        result.error_message = "Docker部署失败"
                        result.end_time = datetime.datetime.now()
                        return result
            
            # 执行后置自定义命令
            if project_config.custom_commands:
                self._execute_custom_commands(project_config.custom_commands, project_path, "post")
            
            # 记录成功更新
            self.rollback_info[project_name].update({
                "status": "success",
                "update_end": datetime.datetime.now().isoformat(),
                "changes_count": result.changes_count
            })
            self.save_rollback_info()
            
            self._log_safe("info", f"🎉 {project_name} 更新完成! (耗时: {result.duration:.1f}秒)")
            result.status = UpdateStatus.SUCCESS
            result.end_time = datetime.datetime.now()
            
        except KeyboardInterrupt:
            self._log_safe("warning", f"用户中断更新: {project_name}")
            result.status = UpdateStatus.CANCELLED
            result.error_message = "用户中断"
            result.end_time = datetime.datetime.now()
            self.shutdown_event.set()  # 设置关闭事件
            raise
            
        except Exception as e:
            self._log_safe("error", f"更新 {project_name} 时发生异常: {str(e)}", exc_info=True)
            self.rollback_info[project_name]["status"] = "exception"
            self.rollback_info[project_name]["error"] = str(e)
            self.save_rollback_info()
            result.status = UpdateStatus.FAILED
            result.error_message = str(e)
            result.end_time = datetime.datetime.now()
            
        return result
    
    def _confirm_update(self, project_name: str) -> bool:
        """交互模式确认更新"""
        try:
            response = input(f"确认更新项目 {project_name}? [y/N]: ").strip().lower()
            return response in ['y', 'yes']
        except (EOFError, KeyboardInterrupt):
            return False
    
    def _get_git_changes(self, project_path: Path) -> List[str]:
        """获取Git变更文件列表"""
        try:
            success, stdout, _ = self.run_command(
                ["git", "diff", "--name-only", "HEAD~1..HEAD"],
                project_path
            )
            if success and stdout:
                return stdout.strip().split('\n')
        except:
            pass
        return []
    
    def _perform_git_update(self, project_name: str, project_config: ProjectConfig, 
                           project_path: Path, result: UpdateResult) -> UpdateStatus:
        """执行Git更新流程"""
        self._log_safe("info", f"开始Git更新: {project_name}")
        
        # 使用全局锁保护共享Git操作
        with _global_git_lock:
            # 记录初始提交
            initial_commit = self.get_current_commit(project_path)
            
            # 1. 检查Git状态
            if not self.check_git_status(project_path, project_config, result):
                return UpdateStatus.FAILED
            
            # 2. 创建备份分支
            if self.config.getboolean('general', 'backup_before_update', fallback=True):
                backup_branch = self._create_backup_branch(project_path)
                result.backup_branch = backup_branch
                self._create_backup(project_name, project_path)
                self.create_git_checkpoint(project_path, GitCheckpointType.BEFORE_UPDATE)
            
            # 3. 设置Git远程仓库
            if not self.setup_git_remotes(project_name):
                self._log_safe("error", "设置Git远程仓库失败")
                self._handle_git_failure(project_path, "setup_remotes")
                return UpdateStatus.FAILED
            
            # 4. 创建远程设置后检查点
            self.create_git_checkpoint(project_path, GitCheckpointType.AFTER_REMOTE_SETUP)
            
            # 5. 获取上游更改
            if not self.fetch_upstream_changes(project_path, project_config):
                self._log_safe("error", "获取上游更改失败")
                self._handle_git_failure(project_path, "fetch_upstream")
                return UpdateStatus.FAILED
            
            # 6. 创建获取后检查点
            self.create_git_checkpoint(project_path, GitCheckpointType.AFTER_FETCH)
            
            # 7. 合并上游更改
            merge_result = self.merge_upstream_changes(project_path, project_config.branch)
            if merge_result == "failed":
                self._log_safe("error", "合并上游更改失败")
                self._handle_git_failure(project_path, "merge_upstream")
                return UpdateStatus.FAILED
            elif merge_result == "no_changes":
                self._log_safe("info", f"{project_name} 已是最新版本，无需更新")
                self.rollback_info[project_name]["git_update_success"] = True
                self.rollback_info[project_name]["has_changes"] = False
                return UpdateStatus.NO_CHANGES
            
            # 8. 创建合并后检查点
            self.create_git_checkpoint(project_path, GitCheckpointType.AFTER_MERGE)
            
            # 9. 推送到自己的仓库
            force_push = self.config.getboolean('general', 'force_push', fallback=False)
            if not self.push_to_origin(project_path, project_config.branch, force=force_push):
                self._log_safe("error", "推送到远程仓库失败")
                self._handle_git_failure(project_path, "push_origin")
                return UpdateStatus.FAILED
            
            # 10. 创建推送后检查点
            self.create_git_checkpoint(project_path, GitCheckpointType.AFTER_PUSH)
            
            # 11. 记录最终提交
            final_commit = self.get_current_commit(project_path)
            if final_commit:
                self.rollback_info[project_name].update({
                    "before_update_commit": initial_commit,
                    "after_update_commit": final_commit,
                    "git_update_success": True,
                    "has_changes": initial_commit != final_commit
                })
            
            self._log_safe("info", f"Git更新成功: {project_name}")
            return UpdateStatus.SUCCESS
    
    def _create_backup(self, project_name: str, project_path: Path):
        """创建项目备份"""
        try:
            if not self.config.getboolean('general', 'create_restore_points', fallback=True):
                return
                
            # 确保备份目录存在
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            
            backup_name = f"{project_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # 检查仓库大小，大型仓库可能跳过备份
            try:
                size_check = subprocess.run([
                    "git", "count-objects", "-v"
                ], cwd=project_path, capture_output=True, text=True, timeout=10)
                
                if size_check.returncode == 0 and "size-pack" in size_check.stdout:
                    # 简单的大小检查，如果超过500MB跳过bundle备份
                    for line in size_check.stdout.split('\n'):
                        if 'size-pack' in line:
                            size_kb = int(line.split()[1])
                            if size_kb > 500000:  # 500MB
                                self._log_safe("warning", f"仓库较大({size_kb}KB)，跳过bundle备份")
                                return
            except:
                pass  # 如果检查失败，继续创建备份
            
            bundle_file = self.backup_dir / f"{backup_name}.bundle"
            
            # 创建Git bundle备份
            self._log_safe("info", f"创建Git bundle备份: {backup_name}")
            
            success, _, _ = self.run_command(
                ["git", "bundle", "create", str(bundle_file), "--all"],
                project_path
            )
            
            if success:
                self._log_safe("info", f"备份创建成功: {bundle_file}")
                # 清理旧备份
                self._cleanup_old_backups(project_name)
            else:
                self._log_safe("warning", "备份创建失败")
                
        except Exception as e:
            self._log_safe("warning", f"创建备份时发生异常: {str(e)}")
    
    def _cleanup_old_backups(self, project_name: str):
        """清理旧备份"""
        try:
            max_age_days = self.config.getint('general', 'max_backup_age_days', fallback=30)
            cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
            
            for backup_file in self.backup_dir.glob(f"{project_name}_*.bundle"):
                if backup_file.stat().st_mtime < cutoff_time:
                    backup_file.unlink()
                    self._log_safe("info", f"删除旧备份: {backup_file.name}")
                    
        except Exception as e:
            self._log_safe("warning", f"清理旧备份失败: {str(e)}")
    
    def _perform_docker_deployment(self, project_name: str, project_path: Path) -> bool:
        """执行Docker部署"""
        self._log_safe("info", f"开始Docker部署: {project_name}")
        
        # 使用Docker锁防止并发问题
        with _global_docker_lock:
            # 检查配置文件是否变更
            config_changed = self._check_docker_config_changed(project_path)
            
            # 停止现有服务
            if not self.stop_docker_services(project_path):
                self._log_safe("error", "停止Docker服务失败")
                return False
            
            # 如果配置变更，清理旧镜像
            if config_changed and self.config.getboolean('docker', 'rebuild_on_config_change', fallback=True):
                self._log_safe("info", "检测到Docker配置变更，清理旧镜像...")
                self._clean_docker_images(project_path)
            
            # 重新构建并启动
            if not self.rebuild_and_start_docker(project_path, project_name):
                self._log_safe("error", "重新构建Docker应用失败")
                return False
            
            self.rollback_info[project_name]["docker_deploy_success"] = True
            self._log_safe("info", f"Docker部署成功: {project_name}")
            return True
    
    def _check_docker_config_changed(self, project_path: Path) -> bool:
        """检查Docker配置是否变更"""
        try:
            # 修复：更健壮的项目配置获取
            project_name = project_path.name
            project_config = None
            
            # 查找匹配的项目配置
            for name, config in self.projects.items():
                if config.path == project_path or config.path.name == project_name:
                    project_config = config
                    break
            
            if not project_config:
                self._log_safe("warning", f"未找到项目配置: {project_name}")
                return False
                
            compose_file = project_config.docker_compose_file
            compose_path = project_path / compose_file
            
            if not compose_path.exists():
                self._log_safe("warning", f"Docker配置文件不存在: {compose_path}")
                return False
            
            # 检查多个配置文件的变更
            config_files = [compose_file]
            
            # 添加其他可能的配置文件
            additional_configs = ['Dockerfile', '.env', 'docker-compose.override.yml', 'requirements.txt']
            for config_file in additional_configs:
                if (project_path / config_file).exists():
                    config_files.append(config_file)
            
            # 计算所有配置文件的联合哈希
            combined_content = b""
            for config_file in config_files:
                config_path = project_path / config_file
                if config_path.exists():
                    try:
                        with open(config_path, 'rb') as f:
                            combined_content += f.read()
                    except Exception as e:
                        self._log_safe("warning", f"读取配置文件失败 {config_file}: {str(e)}")
                        continue
            
            if not combined_content:
                return False
                
            current_hash = hashlib.md5(combined_content).hexdigest()
            
            # 比较缓存的哈希
            cache_file = self.cache_dir / f"{project_name}_docker_config.hash"
            try:
                if cache_file.exists():
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cached_hash = f.read().strip()
                        
                    if current_hash != cached_hash:
                        # 更新缓存
                        with open(cache_file, 'w', encoding='utf-8') as f:
                            f.write(current_hash)
                        self._log_safe("info", f"检测到Docker配置变更: {project_name}")
                        return True
                    else:
                        return False
                else:
                    # 首次运行，保存哈希
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        f.write(current_hash)
                    return False  # 首次运行不算变更
                    
            except Exception as e:
                self._log_safe("warning", f"处理配置哈希缓存失败: {str(e)}")
                return False
                
        except Exception as e:
            self._log_safe("warning", f"检查Docker配置变更失败: {str(e)}")
            return False
    
    def _clean_docker_images(self, project_path: Path):
        """清理项目相关的Docker镜像"""
        try:
            prune_scope = self.config.get('docker', 'prune_scope', fallback='project')
            
            if prune_scope == 'project':
                # 仅清理项目相关的镜像
                success, stdout, _ = self.run_command(
                    self.docker_compose_cmd + ["images", "-q"],
                    project_path
                )
                
                if success and stdout:
                    image_ids = stdout.strip().split('\n')
                    for image_id in image_ids:
                        if image_id:
                            self.run_command(["docker", "rmi", "-f", image_id])
            elif prune_scope == 'global':
                # 全局清理（谨慎使用）
                self._prune_docker_resources()
                        
        except Exception as e:
            self._log_safe("warning", f"清理Docker镜像失败: {str(e)}")
    
    def get_current_commit(self, project_path: Path) -> Optional[str]:
        """获取当前提交ID"""
        success, commit_hash, _ = self.run_command(["git", "rev-parse", "HEAD"], project_path)
        if success:
            return commit_hash.strip()
        return None
    
    def check_git_status(self, project_path: Path, project_config: ProjectConfig, result: UpdateResult) -> bool:
        """检查Git仓库状态"""
        self._log_safe("info", f"检查 {project_path.name} Git 状态...")
        
        # 检查是否为Git仓库
        if not (project_path / ".git").exists():
            if project_config.is_git_repo:
                self._log_safe("warning", f"{project_path} 不是Git仓库，尝试初始化...")
                return self._initialize_git_repo(project_path)
            else:
                self._log_safe("info", f"{project_path} 不是Git项目，跳过Git操作")
                return True
            
        # 检查是否有未提交的更改
        success, stdout, _ = self.run_command(["git", "status", "--porcelain"], project_path)
        if not success:
            self._log_safe("error", f"无法获取Git状态")
            return False
            
        if stdout.strip():
            # 记录被覆盖的文件
            changed_files = [line.strip() for line in stdout.strip().split('\n')]
            self._log_safe("warning", f"{project_path.name} 有未提交的更改:")
            for file_change in changed_files:
                self._log_safe("warning", f"  {file_change}")
            
            if project_config.auto_stash:
                self._log_safe("info", "自动暂存未提交的更改...")
                stash_ref = self._safe_stash_changes(project_path)
                if stash_ref:
                    result.stash_ref = stash_ref
                    with self.data_lock:
                        self.rollback_info[project_path.name] = {
                            "has_stash": True,
                            "stash_ref": stash_ref,
                            "stash_time": datetime.datetime.now().isoformat()
                        }
                    
                    # 清理旧的自动stash（保留最近5个）
                    self._cleanup_old_stashes(project_path)
                    
                else:
                    self._log_safe("error", "暂存更改失败")
                    return False
            else:
                # 安全合并模式下拒绝有未提交更改的操作
                if self.config.getboolean('general', 'safe_merge_only', fallback=False):
                    self._log_safe("error", "安全合并模式下不允许有未提交的更改")
                    return False
                    
                # 保存当前状态用于回滚
                with self.data_lock:
                    self.rollback_info[project_path.name] = {
                        "uncommitted_changes": stdout,
                        "timestamp": datetime.datetime.now().isoformat()
                    }
            
        return True
    
    def _cleanup_old_stashes(self, project_path: Path):
        """清理旧的自动stash"""
        try:
            # 获取所有stash
            success, stash_output, _ = self.run_command(["git", "stash", "list"], project_path)
            if success and stash_output:
                auto_stash_lines = []
                for line in stash_output.strip().split('\n'):
                    if "VCP auto-updater stash" in line:
                        auto_stash_lines.append(line)
                
                # 保留最近5个，删除其余的
                if len(auto_stash_lines) > 5:
                    for i in range(len(auto_stash_lines) - 5):
                        stash_ref = auto_stash_lines[i].split(':')[0].strip()
                        self.run_command(["git", "stash", "drop", stash_ref], project_path)
                        self._log_safe("info", f"删除旧的自动stash: {stash_ref}")
        except Exception as e:
            self._log_safe("warning", f"清理旧stash失败: {str(e)}")
    
    def _initialize_git_repo(self, project_path: Path) -> bool:
        """初始化Git仓库"""
        self._log_safe("info", f"初始化 {project_path.name} Git仓库...")
        
        try:
            # 初始化Git仓库
            success, _, stderr = self.run_command(["git", "init"], project_path)
            if not success:
                self._log_safe("error", f"Git初始化失败: {stderr}")
                return False
        
            # 检查Git用户信息是否已配置 - 修正逻辑
            success_name, existing_name, _ = self.run_command(["git", "config", "user.name"], project_path)
            success_email, existing_email, _ = self.run_command(["git", "config", "user.email"], project_path)

            if not (success_name and existing_name.strip()) or not (success_email and existing_email.strip()):
                # 只有在未配置时才设置默认值
                self.run_command(["git", "config", "user.name", "VCP Auto Updater"], project_path)
                self.run_command(["git", "config", "user.email", "vcp-updater@localhost"], project_path)
                
            # 添加所有文件
            success, _, stderr = self.run_command(["git", "add", "."], project_path)
            if not success:
                self._log_safe("error", f"添加文件失败: {stderr}")
                return False
            
            # 创建初始提交
            success, _, stderr = self.run_command([
                "git", "commit", "-m", f"Initial commit by VCP auto-updater {__version__}"
            ], project_path)
            if not success:
                self._log_safe("error", f"创建初始提交失败: {stderr}")
                return False
            
            # 设置默认分支为main
            success, _, stderr = self.run_command([
                "git", "branch", "-M", "main"
            ], project_path)
            if not success:
                self._log_safe("warning", f"设置主分支失败: {stderr}")
            
            self._log_safe("info", f"Git仓库初始化成功: {project_path.name}")
            return True
            
        except Exception as e:
            self._log_safe("error", f"初始化Git仓库时发生异常: {str(e)}")
            return False
    
    def setup_git_remotes(self, project_name: str) -> bool:
        """设置Git远程仓库"""
        project_config = self.projects[project_name]
        project_path = project_config.path
        
        self._log_safe("info", f"设置 {project_name} Git 远程仓库...")
        
        # 设置upstream
        if not self._setup_git_remote(project_path, "upstream", project_config.upstream_url):
            return False
            
        # 设置origin
        if not self._setup_git_remote(project_path, "origin", project_config.origin_url):
            return False
            
        return True
    
    def _setup_git_remote(self, project_path: Path, remote_name: str, remote_url: str) -> bool:
        """设置单个Git远程仓库"""
        success, current_url, _ = self.run_command(
            ["git", "remote", "get-url", remote_name], 
            project_path
        )
        
        if success:
            current_url = current_url.strip()
            if current_url != remote_url:
                self._log_safe("info", f"更新 '{remote_name}' 远程仓库URL...")
                success, _, stderr = self.run_command([
                    "git", "remote", "set-url", remote_name, remote_url
                ], project_path)
                if not success:
                    self._log_safe("error", f"更新远程仓库URL失败: {stderr}")
                    return False
            self._log_safe("info", f"'{remote_name}' 远程仓库已配置: {remote_url}")
        else:
            self._log_safe("info", f"添加 '{remote_name}' 远程仓库...")
            success, _, stderr = self.run_command([
                "git", "remote", "add", remote_name, remote_url
            ], project_path)
            if not success:
                self._log_safe("error", f"添加远程仓库失败: {stderr}")
                return False
            self._log_safe("info", f"已添加 '{remote_name}' 远程仓库: {remote_url}")
            
        return True
    
    def fetch_upstream_changes(self, project_path: Path, project_config: ProjectConfig) -> bool:
        """获取上游更改"""
        self._log_safe("info", f"获取 {project_path.name} 上游更改...")
        
        # 设置SSL配置
        if not self.config.getboolean('network', 'ssl_verify', fallback=True):
            self.run_command(["git", "config", "--local", "http.sslVerify", "false"], project_path)
        
        # 尝试获取更改（默认启用重试）
        success, stdout, stderr = self.run_command(
            ["git", "fetch", "upstream", "--tags", "--prune"],
            project_path,
            timeout=self.git_timeout,
            retry_on_failure=True
        )
        
        if not success:
            # 尝试处理常见错误
            if "ssl" in stderr.lower() or "tls" in stderr.lower():
                self._log_safe("warning", "检测到SSL/TLS问题，尝试调整配置...")
                self._configure_git_ssl(project_path)
                
                # 重试
                success, stdout, stderr = self.run_command(
                    ["git", "fetch", "upstream", "--tags", "--prune"],
                    project_path,
                    timeout=self.git_timeout * 2
                )
        
        if success:
            self._log_safe("info", "成功获取上游更改")
            return True
        else:
            self._log_safe("error", f"获取上游更改失败: {stderr}")
            return False
    
    def _configure_git_ssl(self, project_path: Path):
        """配置Git SSL设置"""
        ssl_configs = [
            ["git", "config", "--local", "http.sslBackend", "openssl"],
            ["git", "config", "--local", "http.postBuffer", "524288000"],
            ["git", "config", "--local", "http.version", "HTTP/1.1"]
        ]
        
        for config_cmd in ssl_configs:
            self.run_command(config_cmd, project_path)
    
    def merge_upstream_changes(self, project_path: Path, branch: str = "main") -> str:
        """合并上游更改"""
        self._log_safe("info", f"合并 {project_path.name} 上游更改...")
        
        # 检查是否配置自动合并冲突
        auto_merge = self.config.getboolean('general', 'auto_merge_conflicts', fallback=True)
        
        # 首先尝试普通合并
        success, stdout, stderr = self.run_command([
            "git", "merge", f"upstream/{branch}", "--no-edit"
        ], project_path)

        if success:
            if "Already up to date" in stdout or "Already up-to-date" in stdout:
                self._log_safe("info", "已是最新版本，无需更新")
                return "no_changes"
            else:
                self._log_safe("info", "成功合并上游更改")
                return "success"

        # 合并失败处理
        if "conflict" in stderr.lower() or "unrelated histories" in stderr.lower():
            if not auto_merge:
                self._log_safe("error", "检测到合并冲突，但自动合并已禁用")
                return "failed"
                
            self._log_safe("warning", "检测到合并冲突，尝试自动解决...")
            self._log_safe("warning", "注意：将使用上游版本覆盖本地更改")
            
            # 取消当前合并
            self.run_command(["git", "merge", "--abort"], project_path)
            
            # 使用策略合并 - 修正参数格式
            strategies = [
                ["git", "merge", f"upstream/{branch}", "--strategy=recursive", 
                 "-X", "theirs", "--no-edit"],  # 使用 -X theirs
                ["git", "reset", "--hard", f"upstream/{branch}"]
            ]
            
            for strategy in strategies:
                self._log_safe("info", f"尝试策略: {' '.join(strategy)}")
                success, _, _ = self.run_command(strategy, project_path)
                if success:
                    self._log_safe("info", "成功解决合并冲突")
                    return "success"
            
            self._log_safe("error", "无法自动解决合并冲突")
            return "failed"
        else:
            self._log_safe("error", f"合并失败: {stderr}")
            return "failed"
    
    def push_to_origin(self, project_path: Path, branch: str = "main", force: bool = False) -> bool:
        """推送到远程仓库"""
        self._log_safe("info", f"推送 {project_path.name} 到远程仓库...")
        
        push_cmd = ["git", "push"]
        if force:
            push_cmd.append("--force-with-lease")
            self._log_safe("warning", "使用安全强制推送模式")
        push_cmd.extend(["origin", branch])
        push_cmd.append("--tags")
        
        success, stdout, stderr = self.run_command(
            push_cmd, 
            project_path,
            retry_on_failure=True
        )
        
        if not success:
            # 检查是否是因为没有更改
            if "Everything up-to-date" in stderr or "Everything up-to-date" in stdout:
                self._log_safe("info", "远程仓库已是最新状态")
                return True
            self._log_safe("error", f"推送失败: {stderr}")
            return False
            
        self._log_safe("info", "成功推送到远程仓库")
        return True
    
    def create_git_checkpoint(self, project_path: Path, checkpoint_type: GitCheckpointType, 
                            description: str = "") -> Optional[str]:
        """创建Git检查点"""
        checkpoint_name = checkpoint_type.value
        self._log_safe("info", f"创建Git检查点: {checkpoint_name}")
        
        # 获取当前提交
        commit_hash = self.get_current_commit(project_path)
        if not commit_hash:
            self._log_safe("error", "无法获取当前提交")
            return None
        
        # 获取当前分支
        success, branch, _ = self.run_command(["git", "branch", "--show-current"], project_path)
        if not success:
            branch = "main"
        
        # 检查是否有未暂存的更改
        success, status_output, _ = self.run_command(["git", "status", "--porcelain"], project_path)
        has_uncommitted = bool(status_output.strip()) if success else False
        
        # 创建标签（如果配置允许）
        if self.config.getboolean('general', 'create_restore_points', fallback=True):
            tag_name = f"vcp-checkpoint-{checkpoint_name}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            tag_message = description or f"VCP checkpoint: {checkpoint_name}"
            self.run_command([
                "git", "tag", "-a", tag_name, "-m", tag_message
            ], project_path)
            
            # 可选：推送标签到远程（如果配置允许）
            if self.config.getboolean('general', 'push_checkpoints', fallback=False):
                self.run_command(["git", "push", "origin", tag_name], project_path)
        
        checkpoint_info = {
            "commit_hash": commit_hash.strip(),
            "branch": branch.strip(),
            "has_uncommitted_changes": has_uncommitted,
            "uncommitted_changes": status_output if has_uncommitted else "",
            "timestamp": datetime.datetime.now().isoformat(),
            "checkpoint_type": checkpoint_type.value,
            "description": description,
            "version": __version__
        }
        
        project_name = project_path.name
        if project_name not in self.git_checkpoints:
            self.git_checkpoints[project_name] = {}
        
        self.git_checkpoints[project_name][checkpoint_name] = checkpoint_info
        self.save_rollback_info()
        
        self._log_safe("info", f"检查点已创建: {checkpoint_name} -> {commit_hash[:8]}")
        return commit_hash
    
    def restore_git_checkpoint(self, project_path: Path, checkpoint_name: str) -> bool:
        """恢复到指定Git检查点"""
        project_name = project_path.name
        
        if (project_name not in self.git_checkpoints or 
            checkpoint_name not in self.git_checkpoints[project_name]):
            self._log_safe("error", f"未找到检查点: {project_name}/{checkpoint_name}")
            return False
        
        checkpoint = self.git_checkpoints[project_name][checkpoint_name]
        self._log_safe("info", f"恢复到检查点: {checkpoint_name} ({checkpoint['commit_hash'][:8]})")
        
        try:
            # 首先保存当前状态
            self.create_git_checkpoint(project_path, GitCheckpointType.AUTO_BACKUP, 
                                     "Auto backup before restore")
            
            # 清理工作区
            self.run_command(["git", "clean", "-fd"], project_path)
            self.run_command(["git", "reset", "--hard"], project_path)
            
            # 取消任何进行中的操作
            self.run_command(["git", "merge", "--abort"], project_path)
            self.run_command(["git", "rebase", "--abort"], project_path)
            self.run_command(["git", "cherry-pick", "--abort"], project_path)
            
            # 切换到目标分支
            if checkpoint.get("branch"):
                self.run_command(["git", "checkout", checkpoint["branch"]], project_path)
            
            # 重置到检查点
            success, _, stderr = self.run_command([
                "git", "reset", "--hard", checkpoint["commit_hash"]
            ], project_path)
            
            if not success:
                self._log_safe("error", f"恢复检查点失败: {stderr}")
                return False
            
            # 恢复暂存的更改（如果有）- 改进的stash处理
            if project_name in self.rollback_info:
                rollback_data = self.rollback_info[project_name]
                if rollback_data.get("has_stash") and rollback_data.get("stash_ref"):
                    self._log_safe("info", f"恢复暂存的更改: {rollback_data['stash_ref']}")
                    # 使用apply而非pop以保留stash
                    success, _, stderr = self.run_command([
                        "git", "stash", "apply", rollback_data["stash_ref"]
                    ], project_path)
                    if not success:
                        self._log_safe("warning", f"恢复stash失败: {stderr}")
            
            self._log_safe("info", f"已恢复到检查点: {checkpoint_name}")
            return True
            
        except Exception as e:
            self._log_safe("error", f"恢复检查点时发生异常: {str(e)}")
            return False

    def cleanup_old_checkpoints(self, project_path: Path, keep_count: int = 10):
        """清理旧的检查点标签"""
        try:
            # 获取所有VCP检查点标签
            success, stdout, _ = self.run_command([
                "git", "tag", "-l", "vcp-checkpoint-*", "--sort=-creatordate"
            ], project_path)
            
            if success and stdout:
                tags = stdout.strip().split('\n')
                if len(tags) > keep_count:
                    # 删除旧标签
                    for tag in tags[keep_count:]:
                        self.run_command(["git", "tag", "-d", tag], project_path)
                        self._log_safe("info", f"删除旧检查点标签: {tag}")
        except Exception as e:
            self._log_safe("warning", f"清理检查点标签失败: {str(e)}")
    
    def stop_docker_services(self, project_path: Path) -> bool:
        """停止Docker服务"""
        self._log_safe("info", f"停止 {project_path.name} Docker服务...")
        
        if not self.check_docker_availability():
            self._log_safe("warning", "Docker不可用，跳过停止操作")
            return True
        
        # 获取配置
        remove_orphans = self.config.getboolean('docker', 'remove_orphans', fallback=True)
        
        cmd = self.docker_compose_cmd + ["down"]
        if remove_orphans:
            cmd.append("--remove-orphans")
        
        success, _, stderr = self.run_command(cmd, project_path, capture_output=False)
        
        if not success:
            self._log_safe("warning", f"停止Docker服务可能失败: {stderr}")
        else:
            self._log_safe("info", "Docker服务已停止")
            
        return True
    
    def rebuild_and_start_docker(self, project_path: Path, project_name: str) -> bool:
        """重新构建并启动Docker应用"""
        self._log_safe("info", f"重新构建并启动 {project_name} Docker应用...")
        
        if not self.check_docker_availability():
            self._log_safe("error", "Docker不可用")
            return False
        
        # 清理旧镜像（如果配置允许）
        if self.config.getboolean('docker', 'auto_prune', fallback=False):
            self._clean_docker_images(project_path)
        
        # 获取重启策略
        max_attempts = self.config.getint('docker', 'max_restart_attempts', fallback=3)
        
        # 尝试启动Docker服务
        for attempt in range(max_attempts):
            if self.shutdown_event.is_set():
                return False
                
            if attempt > 0:
                self._log_safe("info", f"重试启动Docker服务 (尝试 {attempt + 1}/{max_attempts})...")
                time.sleep(5)
            
            # 构建并启动
            cmd = self.docker_compose_cmd + ["up", "--build", "-d"]
            if self.config.getboolean('docker', 'remove_orphans', fallback=True):
                cmd.append("--remove-orphans")
                
            success, _, stderr = self.run_command(
                cmd, 
                project_path, 
                capture_output=False, 
                timeout=self.docker_timeout
            )
            
            if success:
                # 验证健康状态
                if self.verify_docker_health(project_path, project_name):
                    self._log_safe("info", "Docker应用已成功部署")
                    return True
                else:
                    self._log_safe("warning", "Docker容器未通过健康检查")
                    if attempt < max_attempts - 1:
                        self.stop_docker_services(project_path)
            else:
                self._log_safe("error", f"Docker应用启动失败: {stderr}")
        
        self._log_safe("error", f"Docker应用启动失败，已尝试{max_attempts}次")
        return False
    
    def _prune_docker_resources(self):
        """清理Docker资源"""
        try:
            # 清理未使用的镜像
            self.run_command(["docker", "image", "prune", "-f"], timeout=30)
            
            # 清理未使用的容器
            self.run_command(["docker", "container", "prune", "-f"], timeout=30)
            
            # 清理未使用的网络
            self.run_command(["docker", "network", "prune", "-f"], timeout=30)
            
        except Exception as e:
            self._log_safe("warning", f"清理Docker资源失败: {str(e)}")
    
    def verify_docker_health(self, project_path: Path, project_name: str) -> bool:
        """验证Docker容器健康状态"""
        if not self.config.getboolean('general', 'verify_docker_health', fallback=True):
            return True
        
        self._log_safe("info", f"验证 {project_name} Docker容器健康状态...")
        
        project_config = self.projects.get(project_name)
        if not project_config:
            return False
        
        # 等待容器启动
        wait_time = self.config.getint('docker', 'wait_before_health_check', fallback=10)
        self._log_safe("info", f"等待 {wait_time} 秒让容器启动...")
        time.sleep(wait_time)
        
        # 使用简单健康检查
        if self.config.getboolean('docker', 'use_simple_health_check', fallback=True):
            return self._simple_health_check(project_path, project_config)
        else:
            return self._detailed_health_check(project_path, project_config)
    
    def _simple_health_check(self, project_path: Path, project_config: ProjectConfig) -> bool:
        """简单的健康检查"""
        self._log_safe("info", "执行简单健康检查...")
        
        # 检查容器是否在运行
        success, stdout, _ = self.run_command(
            self.docker_compose_cmd + ["ps"],
            project_path
        )
        
        if success and stdout:
            # 检查输出中是否包含运行状态（支持更多状态）
            running_pattern = re.compile(r'\b(Up|running|healthy)\b', re.IGNORECASE)
            exit_pattern = re.compile(r'\b(Exit|exited|stopped|dead)\b', re.IGNORECASE)
            
            if running_pattern.search(stdout) and not exit_pattern.search(stdout):
                self._log_safe("info", "容器运行正常")
                
                # 如果配置了端口，尝试检查端口
                if project_config.docker_port:
                    if self._check_port(project_config.docker_port):
                        self._log_safe("info", f"端口 {project_config.docker_port} 可访问")
                        return True
                    else:
                        self._log_safe("warning", f"端口 {project_config.docker_port} 暂时不可访问")
                        # 给容器更多启动时间
                        time.sleep(5)
                        if self._check_port(project_config.docker_port):
                            return True
                        return True  # 即使端口不可访问，只要容器运行也认为成功
                
                return True
        
        self._log_safe("error", "容器未在运行状态")
        return False
    
    def _detailed_health_check(self, project_path: Path, project_config: ProjectConfig) -> bool:
        """详细的健康检查"""
        timeout = project_config.docker_health_check_timeout
        interval = project_config.docker_health_check_interval
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.shutdown_event.is_set():
                return False
                
            # 首先尝试使用 JSON 格式
            success, stdout, _ = self.run_command(
                self.docker_compose_cmd + ["ps", "--format", "json"],
                project_path
            )
            
            if not success:
                # 如果 JSON 格式不支持，降级到普通格式
                success, stdout, _ = self.run_command(
                    self.docker_compose_cmd + ["ps"],
                    project_path
                )
                if success:
                    return self._simple_health_check(project_path, project_config)
                
            if success and stdout:
                try:
                    # 尝试解析JSON格式
                    containers = json.loads(stdout)
                    if isinstance(containers, list):
                        all_healthy = True
                        for container in containers:
                            state = container.get('State', '').lower()
                            health = container.get('Health', '').lower()
                            
                            if state == 'running' and (not health or health == 'healthy'):
                                continue
                            elif state == 'restarting':
                                self._log_safe("warning", f"容器正在重启: {container.get('Service', 'unknown')}")
                                all_healthy = False
                            elif state == 'exited':
                                self._log_safe("error", f"容器已退出: {container.get('Service', 'unknown')}")
                                return False
                            else:
                                all_healthy = False
                        
                        if all_healthy:
                            self._log_safe("info", "所有容器运行正常")
                            return True
                            
                except json.JSONDecodeError as e:
                    self._log_safe("warning", f"Docker输出不是有效的JSON格式: {e}")
                    self._log_safe("debug", f"原始输出: {stdout[:200]}...")
                    # 降级到基本检查
                    return self._simple_health_check(project_path, project_config)
            
            time.sleep(interval)
        
        self._log_safe("error", f"Docker容器健康检查超时 ({timeout}秒)")
        return False
    
    def _check_port(self, port: int, host: str = 'localhost') -> bool:
        """检查端口是否可访问"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        try:
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except:
            return False
    
    def _handle_git_failure(self, project_path: Path, failure_stage: str):
        """处理Git操作失败"""
        self._log_safe("warning", f"Git操作失败，阶段: {failure_stage}")
        
        # 清理Git状态
        try:
            self.run_command(["git", "merge", "--abort"], project_path)
            self.run_command(["git", "rebase", "--abort"], project_path)
            self.run_command(["git", "cherry-pick", "--abort"], project_path)
            self.run_command(["git", "reset", "--hard"], project_path)
        except Exception as e:
            self._log_safe("warning", f"清理Git状态时发生异常: {str(e)}")
        
        # 尝试恢复到最近的安全检查点
        checkpoints_priority = [
            GitCheckpointType.AFTER_PUSH.value,
            GitCheckpointType.AFTER_MERGE.value,
            GitCheckpointType.AFTER_FETCH.value,
            GitCheckpointType.AFTER_REMOTE_SETUP.value,
            GitCheckpointType.BEFORE_UPDATE.value
        ]
        
        for checkpoint in checkpoints_priority:
            if self.restore_git_checkpoint(project_path, checkpoint):
                self._log_safe("info", f"已恢复到检查点: {checkpoint}")
                break
        else:
            self._log_safe("error", "无法恢复到任何检查点")
    
    def save_rollback_info(self):
        """保存回滚信息"""
        try:
            combined_info = {
                "version": __version__,
                "rollback_info": self.rollback_info,
                "git_checkpoints": self.git_checkpoints,
                "last_update": datetime.datetime.now().isoformat(),
                "update_stats": dict(self.update_stats),
                "update_results": [asdict(r) for r in self.update_results[-10:]]  # 保存最近10次结果
            }
            
            # 使用临时文件避免写入失败导致数据丢失
            temp_file = self.rollback_info_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(combined_info, f, ensure_ascii=False, indent=2, default=str)
            
            # 原子性替换
            temp_file.replace(self.rollback_info_file)
            
            self._log_safe("debug", f"回滚信息已保存到: {self.rollback_info_file}")
        except Exception as e:
            self._log_safe("error", f"保存回滚信息失败: {str(e)}")
    
    def rollback_project(self, project_name: str) -> bool:
        """回滚项目到更新前状态"""
        self._log_safe("info", f"开始回滚 {project_name}...")
        
        # 使用"before_update"检查点进行回滚
        if self.restore_to_checkpoint(project_name, GitCheckpointType.BEFORE_UPDATE.value):
            self._log_safe("info", f"✅ {project_name} 已成功回滚到更新前状态")
            
            # 更新回滚信息
            if project_name in self.rollback_info:
                self.rollback_info[project_name]["last_rollback"] = datetime.datetime.now().isoformat()
                self.save_rollback_info()
                
            return True
        else:
            self._log_safe("error", f"❌ {project_name} 回滚失败!")
            return False
    
    def restore_to_checkpoint(self, project_name: str, checkpoint_name: str) -> bool:
        """恢复到指定检查点"""
        if project_name not in self.projects:
            self._log_safe("error", f"未知项目: {project_name}")
            return False
        
        project_path = self.projects[project_name].path
        
        if self.restore_git_checkpoint(project_path, checkpoint_name):
            # 如果是Docker项目，重新部署
            if self.projects[project_name].has_docker and self.check_docker_availability():
                self._log_safe("info", "检测到Docker项目，重新部署...")
                self.stop_docker_services(project_path)
                self.rebuild_and_start_docker(project_path, project_name)
            
            self._log_safe("info", f"✅ {project_name} 已恢复到检查点: {checkpoint_name}")
            return True
        else:
            return False
    
    def _find_project_by_alias(self, alias: str) -> Optional[str]:
        """通过别名查找项目"""
        alias_lower = alias.lower()
        
        # 精确匹配
        for project_name in self.projects.keys():
            if project_name.lower() == alias_lower:
                return project_name
        
        # 别名匹配
        for base_alias, variations in self.project_aliases.items():
            if alias_lower in variations:
                # 查找匹配的项目
                matches = []
                for project_name in self.projects.keys():
                    project_lower = project_name.lower()
                    if base_alias in project_lower or any(v in project_lower for v in variations):
                        matches.append(project_name)
                
                if len(matches) == 1:
                    return matches[0]
                elif len(matches) > 1:
                    self._log_safe("warning", f"别名 '{alias}' 匹配多个项目: {matches}")
                    return matches[0]  # 返回第一个匹配
        
        return None
    
    def update_all_projects(self, parallel: bool = True) -> bool:
        """更新所有项目"""
        self._log_safe("info", f"开始{'并行' if parallel else '顺序'}更新所有VCP项目...")
        self._log_safe("info", f"项目总数: {len(self.projects)}")
        
        # 重置统计和状态 - 确保清零
        with self.data_lock:
            self.update_stats.clear()
            self.update_results = [r for r in self.update_results if r.start_time and 
                                  r.start_time < datetime.datetime.now() - datetime.timedelta(hours=1)]  # 保留1小时内的历史记录
            self.is_running = True
            self.should_cancel = False
            self.shutdown_event.clear()
        
        start_time = datetime.datetime.now()
        
        try:
            if parallel and self.config.getboolean('performance', 'enable_parallel_git', fallback=True):
                results = self._update_projects_parallel()
            else:
                results = self._update_projects_sequential()
            
            # 保存结果
            with self.data_lock:
                self.update_results.extend(results)
                
                # 重新清零并重新统计，确保准确性
                self.update_stats.clear()
                for result in results:
                    self.update_stats[result.status.value] += 1
            
            # 保存统计信息
            self.save_rollback_info()
            
            # 计算总耗时
            total_duration = (datetime.datetime.now() - start_time).total_seconds()
            
            # 输出统计结果
            self._print_update_summary(results, total_duration)
            
            # 判断整体成功与否
            failed_count = self.update_stats.get(UpdateStatus.FAILED.value, 0)
            cancelled_count = self.update_stats.get(UpdateStatus.CANCELLED.value, 0)
            
            if failed_count == 0 and cancelled_count == 0:
                return True
            else:
                return False
                
        except KeyboardInterrupt:
            self._log_safe("warning", "用户中断更新操作")
            self.should_cancel = True
            self.shutdown_event.set()
            return False
        finally:
            self.is_running = False
    
    def _print_update_summary(self, results: List[UpdateResult], total_duration: float):
        """打印更新摘要"""
        self._log_safe("info", "=" * 60)
        self._log_safe("info", "更新完成统计:")
        self._log_safe("info", f"  总计: {len(results)} 个项目")
        
        # 修复：使用实际结果进行统计，而不是self.update_stats
        actual_stats = defaultdict(int)
        for result in results:
            actual_stats[result.status.value] += 1
        
        for status in UpdateStatus:
            count = actual_stats.get(status.value, 0)
            if count > 0:
                status_display = {
                    UpdateStatus.SUCCESS: "✅ 成功",
                    UpdateStatus.FAILED: "❌ 失败",
                    UpdateStatus.PARTIAL: "⚠️  部分成功",
                    UpdateStatus.SKIPPED: "⏭️  跳过",
                    UpdateStatus.NO_CHANGES: "🔄 无更新",
                    UpdateStatus.CANCELLED: "🚫 已取消"
                }.get(status, status.value)
                self._log_safe("info", f"  {status_display}: {count} 个")
        
        self._log_safe("info", f"  总耗时: {total_duration:.1f} 秒")
        self._log_safe("info", "=" * 60)
        
        # 显示失败的项目详情
        failed_results = [r for r in results if r.status == UpdateStatus.FAILED]
        if failed_results:
            self._log_safe("error", "失败的项目:")
            for result in failed_results:
                self._log_safe("error", f"  - {result.project_name}: {result.error_message or '未知错误'}")
        
        # 显示成功更新的项目变更
        success_results = [r for r in results if r.status == UpdateStatus.SUCCESS and r.changes_count > 0]
        if success_results:
            self._log_safe("info", "成功更新的项目:")
            for result in success_results:
                self._log_safe("info", f"  - {result.project_name}: {result.changes_count} 个文件变更")
    
    def _update_projects_sequential(self) -> List[UpdateResult]:
        """顺序更新项目"""
        results = []
        for project_name in self.projects.keys():
            if self.should_cancel or self.shutdown_event.is_set():
                result = UpdateResult(
                    project_name=project_name,
                    status=UpdateStatus.CANCELLED,
                    start_time=datetime.datetime.now(),
                    end_time=datetime.datetime.now()
                )
                results.append(result)
                continue
                
            result = self.update_project(project_name)
            results.append(result)
        return results
    
    def _update_projects_parallel(self) -> List[UpdateResult]:
        """并行更新项目"""
        results = []
        
        # 分离Git操作和Docker操作
        git_projects = list(self.projects.keys())
        docker_projects = [name for name, config in self.projects.items() if config.has_docker]
        
        # 第一阶段：并行执行所有Git更新
        self._log_safe("info", "第一阶段：并行执行Git更新...")
        git_results = {}
        
        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_project = {
                    executor.submit(self._perform_git_update_only, project_name): project_name 
                    for project_name in git_projects
                }
                
                for future in as_completed(future_to_project):
                    if self.shutdown_event.is_set():
                        executor.shutdown(wait=False)
                        break
                        
                    project_name = future_to_project[future]
                    try:
                        result = future.result()
                        git_results[project_name] = result
                        self.safe_log("info", f"Git更新完成: {result.status.value}", project_name)
                    except Exception as e:
                        result = UpdateResult(
                            project_name=project_name,
                            status=UpdateStatus.FAILED,
                            error_message=str(e),
                            start_time=datetime.datetime.now(),
                            end_time=datetime.datetime.now()
                        )
                        git_results[project_name] = result
                        self.safe_log("error", f"Git更新异常: {str(e)}", project_name)
        except Exception as e:
            self._log_safe("error", f"并行Git更新异常: {str(e)}")
        
        # 第二阶段：处理Docker部署
        if docker_projects and self.check_docker_availability() and not self.shutdown_event.is_set():
            parallel_docker = self.config.getboolean('performance', 'enable_parallel_docker', fallback=False)
            
            if parallel_docker:
                self._log_safe("info", "第二阶段：并行执行Docker部署...")
                try:
                    with ThreadPoolExecutor(max_workers=2) as executor:  # 限制Docker并行数
                        docker_futures = []
                        for project_name in docker_projects:
                            if project_name in git_results and git_results[project_name].status in [UpdateStatus.SUCCESS, UpdateStatus.NO_CHANGES]:
                                future = executor.submit(self._perform_docker_update_only, 
                                                       project_name, git_results[project_name])
                                docker_futures.append((future, project_name))
                        
                        for future, project_name in docker_futures:
                            if self.shutdown_event.is_set():
                                executor.shutdown(wait=False)
                                break
                            try:
                                result = future.result()
                                results.append(result)
                            except Exception as e:
                                self.safe_log("error", f"Docker部署异常: {str(e)}", project_name)
                                results.append(git_results[project_name])
                except Exception as e:
                    self._log_safe("error", f"并行Docker部署异常: {str(e)}")
            else:
                self._log_safe("info", "第二阶段：顺序执行Docker部署...")
                for project_name in docker_projects:
                    if self.shutdown_event.is_set():
                        break
                    git_result = git_results.get(project_name)
                    if git_result and git_result.status in [UpdateStatus.SUCCESS, UpdateStatus.NO_CHANGES]:
                        if git_result.status == UpdateStatus.NO_CHANGES and \
                           self.config.getboolean('general', 'skip_unchanged_docker', fallback=True):
                            self.safe_log("info", "代码未更新，跳过Docker重建", project_name)
                            results.append(git_result)
                        else:
                            result = self._perform_docker_update_only(project_name, git_result)
                            results.append(result)
                    else:
                        results.append(git_result)
        
        # 添加非Docker项目的结果
        for project_name in git_projects:
            if project_name not in docker_projects:
                results.append(git_results.get(project_name, UpdateResult(
                    project_name=project_name, 
                    status=UpdateStatus.FAILED,
                    error_message="未找到Git更新结果"
                )))
        
        return results
    
    def _perform_git_update_only(self, project_name: str) -> UpdateResult:
        """仅执行Git更新"""
        result = UpdateResult(
            project_name=project_name,
            status=UpdateStatus.IN_PROGRESS,
            start_time=datetime.datetime.now()
        )
        
        if project_name not in self.projects:
            result.status = UpdateStatus.FAILED
            result.error_message = f"项目未找到: {project_name}，可用项目: {', '.join(self.projects.keys())}"
            result.end_time = datetime.datetime.now()
            return result
        
        project_config = self.projects[project_name]
        project_path = project_config.path
        
        if not project_path.exists():
            result.status = UpdateStatus.FAILED
            result.error_message = "项目路径不存在"
            result.end_time = datetime.datetime.now()
            return result
        
        # 检查origin URL
        if not project_config.origin_url:
            result.status = UpdateStatus.FAILED
            result.error_message = "未配置Fork仓库URL"
            result.end_time = datetime.datetime.now()
            self.safe_log("error", f"请在配置文件[origins]部分设置{project_name.split('-')[0]}的Fork仓库URL", project_name)
            return result
        
        try:
            with self.data_lock:
                self.rollback_info[project_name] = {
                    "update_start": datetime.datetime.now().isoformat(),
                    "status": "in_progress"
                }
            
            git_status = self._perform_git_update(project_name, project_config, project_path, result)
            result.git_status = git_status
            
            if git_status == UpdateStatus.FAILED:
                result.status = UpdateStatus.FAILED
                self.rollback_info[project_name]["status"] = "git_failed"
            elif git_status == UpdateStatus.NO_CHANGES:
                result.status = UpdateStatus.NO_CHANGES
                self.rollback_info[project_name]["status"] = "no_changes"
            else:
                result.status = UpdateStatus.SUCCESS
                self.rollback_info[project_name]["status"] = "git_success"
                
                # 获取变更信息
                changes = self._get_git_changes(project_path)
                result.changes_count = len(changes)
                result.files_changed = changes[:10]
            
            self.save_rollback_info()
            result.end_time = datetime.datetime.now()
            return result
            
        except Exception as e:
            self.safe_log("error", f"Git更新异常: {str(e)}", project_name)
            result.status = UpdateStatus.FAILED
            result.error_message = str(e)
            result.end_time = datetime.datetime.now()
            return result
    
    def _perform_docker_update_only(self, project_name: str, git_result: UpdateResult) -> UpdateResult:
        """仅执行Docker更新"""
        # 复制Git结果
        result = UpdateResult(
            project_name=project_name,
            status=git_result.status,
            git_status=git_result.git_status,
            start_time=git_result.start_time,
            changes_count=git_result.changes_count,
            files_changed=git_result.files_changed,
            backup_branch=git_result.backup_branch,
            stash_ref=git_result.stash_ref
        )
        
        project_config = self.projects[project_name]
        project_path = project_config.path
        
        try:
            docker_success = self._perform_docker_deployment(project_name, project_path)
            result.docker_status = UpdateStatus.SUCCESS if docker_success else UpdateStatus.FAILED
            
            if not docker_success:
                result.status = UpdateStatus.PARTIAL
                result.error_message = "Docker部署失败"
                self.rollback_info[project_name]["status"] = "docker_failed"
            else:
                self.rollback_info[project_name]["status"] = "success"
                
            self.rollback_info[project_name]["update_end"] = datetime.datetime.now().isoformat()
            self.save_rollback_info()
            
        except Exception as e:
            self.safe_log("error", f"Docker部署异常: {str(e)}", project_name)
            result.status = UpdateStatus.PARTIAL
            result.docker_status = UpdateStatus.FAILED
            result.error_message = str(e)
            
        result.end_time = datetime.datetime.now()
        return result
    
    def list_available_checkpoints(self, project_name: str = None) -> Dict:
        """列出可用的检查点"""
        if project_name:
            return self.git_checkpoints.get(project_name, {})
        else:
            return self.git_checkpoints
    
    def rollback_all_projects(self) -> bool:
        """回滚所有项目"""
        self._log_safe("info", "开始回滚所有VCP项目...")
        
        success_count = 0
        total_count = len(self.projects)
        
        for project_name in self.projects.keys():
            if self.rollback_project(project_name):
                success_count += 1
            else:
                self._log_safe("error", f"{project_name} 回滚失败!")
        
        self._log_safe("info", f"回滚完成: {success_count}/{total_count} 个项目成功")
        
        if success_count == total_count:
            self._log_safe("info", "🎉 所有项目回滚成功!")
            return True
        else:
            self._log_safe("warning", "⚠️ 部分项目回滚失败，请检查日志")
            return False
    
    def show_status(self):
        """显示项目状态"""
        status_info = [
            "\n" + "=" * 60,
            f"VCP 自动更新工具 {__version__} - 项目状态",
            "=" * 60,
            f"\n基本信息:",
            f"  VCP根目录: {self.vcp_root}",
            f"  VCPUpdate目录: {self.vcpupdate_path}",
            f"  配置文件: {self.config_file}",
            f"  日志目录: {self.vcpupdate_path / 'update_vcp_logs'}",
            f"\n环境状态:",
            f"  Python版本: {sys.version.split()[0]}",
            f"  Git可用: {'✅ 是' if self.check_git_availability() else '❌ 否'}",
            f"  Docker可用: {'✅ 是' if self.check_docker_availability() else '❌ 否'}",
            f"  Docker Compose命令: {' '.join(self.docker_compose_cmd)}",
            f"\n检测到的项目:"
        ]
        
        for project_name, config in self.projects.items():
            status_info.extend([
                f"\n  📦 {project_name}:",
                f"    路径: {config.path}",
                f"    存在: {'✅ 是' if config.path.exists() else '❌ 否'}",
                f"    Git仓库: {'✅ 是' if config.is_git_repo and (config.path / '.git').exists() else '❌ 否'}",
                f"    Docker支持: {'✅ 是' if config.has_docker else '❌ 否'}",
                f"    上游仓库: {config.upstream_url}",
                f"    Fork仓库: {config.origin_url if config.origin_url else '❌ 未配置'}",
                f"    分支: {config.branch}"
            ])
            
            if config.has_docker:
                status_info.extend([
                    f"    Docker配置: {config.docker_compose_file}"
                ])
                if config.docker_port:
                    status_info.extend([
                        f"    服务端口: {config.docker_port}",
                        f"    端口状态: {'✅ 开放' if self._check_port(config.docker_port) else '❌ 关闭'}"
                    ])
            
            # 显示最后更新信息
            if project_name in self.rollback_info:
                info = self.rollback_info[project_name]
                status = info.get('status', '未知')
                status_display = {
                    'success': '✅ 成功',
                    'git_failed': '❌ Git失败',
                    'docker_failed': '⚠️ Docker失败',
                    'no_changes': '🔄 无更新',
                    'docker_skipped': '⏭️ Docker跳过',
                    'in_progress': '🔄 进行中'
                }.get(status, status)
                
                update_time = info.get('update_start', '未知')
                if update_time != '未知':
                    try:
                        # 格式化时间显示
                        dt = datetime.datetime.fromisoformat(update_time)
                        update_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass
                        
                status_info.extend([
                    f"    最后更新: {status_display} ({update_time})"
                ])
                
                if info.get('changes_count'):
                    status_info.append(f"    变更文件: {info['changes_count']} 个")
        
        # 显示当前运行的统计（如果正在运行）
        if self.is_running:
            status_info.append(f"\n当前运行状态:")
            with self.data_lock:
                current_stats = dict(self.update_stats)
            if current_stats:
                for status_key, count in current_stats.items():
                    if count > 0:
                        status_info.append(f"  {status_key}: {count} 个")
        
        # 显示最近的更新记录
        if self.update_results:
            status_info.append(f"\n最近更新记录:")
            # 只显示最近5条，并过滤重复或无效记录
            recent_results = []
            seen_projects = set()
            
            for result in reversed(self.update_results):
                if result.project_name not in seen_projects and len(recent_results) < 5:
                    recent_results.append(result)
                    seen_projects.add(result.project_name)
            
            for result in reversed(recent_results):
                status_icon = {
                    UpdateStatus.SUCCESS: "✅",
                    UpdateStatus.FAILED: "❌",
                    UpdateStatus.PARTIAL: "⚠️",
                    UpdateStatus.NO_CHANGES: "🔄",
                    UpdateStatus.SKIPPED: "⏭️",
                    UpdateStatus.CANCELLED: "🚫"
                }.get(result.status, "❓")
                
                status_line = f"  {status_icon} {result.project_name}: {result.status.value}"
                if result.duration:
                    status_line += f" (耗时: {result.duration:.1f}秒)"
                if result.changes_count > 0:
                    status_line += f" [{result.changes_count}个文件变更]"
                status_info.append(status_line)
        
        # 显示历史统计（如果有）
        if hasattr(self, '_historical_stats') and self._historical_stats:
            status_info.append(f"\n历史统计摘要:")
            for status_key, count in self._historical_stats.items():
                if count > 0:
                    status_info.append(f"  {status_key}: 累计{count}次")
        
        status_info.append("\n" + "=" * 60)
        
        # 使用print直接输出而不是日志系统
        for line in status_info:
            print(line)
    
    def cleanup_resources(self):
        """清理资源"""
        if self.config.getboolean('general', 'auto_cleanup', fallback=True):
            self._log_safe("info", "执行资源清理...")
            
            # 清理旧日志
            self._cleanup_old_logs(self.vcpupdate_path / "update_vcp_logs")
            
            # 清理旧备份
            for project_name in self.projects.keys():
                self._cleanup_old_backups(project_name)
            
            # 清理Docker资源（仅在配置允许时）
            if self.check_docker_availability() and self.config.getboolean('docker', 'auto_prune', fallback=False):
                self._clean_docker_images(Path())  # 传入空路径表示全局清理
    
    def export_config_template(self, output_file: Path = None):
        """导出配置模板"""
        if not output_file:
            output_file = self.vcpupdate_path / "update_vcp_config_template.ini"
            
        template = configparser.ConfigParser()
        
        # 复制当前配置作为模板
        for section in self.config.sections():
            template[section] = {}
            for option in self.config.options(section):
                value = self.config.get(section, option)
                # 添加注释说明
                if section == 'general' and option == 'auto_merge_conflicts':
                    template.set(section, f"# {option}", "自动解决Git合并冲突")
                elif section == 'docker' and option == 'verify_docker_health':
                    template.set(section, f"# {option}", "验证Docker容器健康状态")
                template.set(section, option, value)
        
        # 添加示例项目配置
        template['projects']['# MyProject'] = json.dumps({
            "path": "MyProject",
            "upstream_url": "https://github.com/original/MyProject.git",
            "origin_url": "https://github.com/yourfork/MyProject.git",
            "has_docker": True,
            "docker_compose_file": "docker-compose.yml",
            "branch": "main"
        }, indent=2)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            template.write(f)
            
        self._log_safe("info", f"配置模板已导出到: {output_file}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description=f"VCP 自动更新工具 {__version__} - 自动从上游同步并部署VCP项目",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                          # 并行更新所有项目
  %(prog)s --project chat           # 只更新VCPChat
  %(prog)s --action rollback        # 回滚所有项目
  %(prog)s --action status          # 查看项目状态
  %(prog)s --config my_config.ini   # 使用自定义配置文件
  
项目别名:
  chat, vcpchat    → VCPChat
  toolbox, tb      → VCPToolBox
        """
    )
    
    parser.add_argument("--project", 
                       help="指定要更新的项目 (支持别名)")
    parser.add_argument("--action", 
                       choices=["update", "rollback", "checkpoint", "list-checkpoints", 
                              "status", "cleanup", "export-config"], 
                       default="update", 
                       help="执行的操作 (默认: update)")
    parser.add_argument("--checkpoint", 
                       help="检查点名称（用于checkpoint操作）")
    parser.add_argument("--vcp-path", 
                       help="VCP根目录路径")
    parser.add_argument("--vcpupdate-path", 
                       help="VCPUpdate目录路径")
    parser.add_argument("--config", 
                       help="配置文件路径")
    parser.add_argument("--parallel", 
                       action="store_true", 
                       default=True, 
                       help="使用并行模式更新（默认启用）")
    parser.add_argument("--sequential", 
                       action="store_true", 
                       help="使用顺序模式更新（禁用并行）")
    parser.add_argument("--force-push", 
                       action="store_true", 
                       help="强制推送到远程仓库")
    parser.add_argument("--skip-docker", 
                       action="store_true", 
                       help="跳过Docker部署步骤")
    parser.add_argument("--interactive", 
                       action="store_true", 
                       help="启用交互模式")
    parser.add_argument("--safe-mode", 
                       action="store_true", 
                       help="启用安全模式（拒绝有未提交更改的操作）")
    parser.add_argument("--version", 
                       action="version", 
                       version=f"%(prog)s {__version__}")
    parser.add_argument("--debug", 
                       action="store_true", 
                       help="启用调试日志")
    
    args = parser.parse_args()
    
    # 处理并行/顺序模式选择
    parallel_mode = args.parallel and not args.sequential
    
    try:
        # 创建更新器实例
        updater = VCPAutoUpdater(args.vcp_path, args.vcpupdate_path, args.config)
        
        # 处理命令行参数覆盖配置
        if args.force_push:
            updater.config.set('general', 'force_push', 'true')
        if args.skip_docker:
            updater.config.set('general', 'verify_docker_health', 'false')
        if args.interactive:
            updater.config.set('general', 'interactive_mode', 'true')
        if args.safe_mode:
            updater.config.set('general', 'safe_merge_only', 'true')
        if args.debug:
            updater.config.set('logging', 'log_level', 'DEBUG')
            updater.config.set('logging', 'enable_debug_logging', 'true')
            # 重新设置日志
            updater.setup_logging()
        
        # 项目名称匹配 - 改进的别名处理
        matched_project = None
        if args.project:
            matched_project = updater._find_project_by_alias(args.project)
            
            if not matched_project:
                updater._log_safe("error", f"未找到项目: {args.project}")
                updater._log_safe("info", f"可用项目: {', '.join(updater.projects.keys())}")
                updater._log_safe("info", f"支持的别名: chat, vcpchat, toolbox, tb")
                sys.exit(1)
        
        # 执行操作
        exit_code = 0
        
        if args.action == "status":
            updater.show_status()
            
        elif args.action == "update":
            if not matched_project:
                success = updater.update_all_projects(parallel=parallel_mode)
            else:
                result = updater.update_project(matched_project)
                success = result.status not in [UpdateStatus.FAILED, UpdateStatus.CANCELLED]
            exit_code = 0 if success else 1
            
        elif args.action == "rollback":
            if not matched_project:
                success = updater.rollback_all_projects()
            else:
                success = updater.rollback_project(matched_project)
            exit_code = 0 if success else 1
            
        elif args.action == "checkpoint":
            if not args.checkpoint:
                updater._log_safe("error", "使用checkpoint操作时必须指定--checkpoint参数")
                sys.exit(1)
            if not matched_project:
                updater._log_safe("error", "checkpoint操作必须指定具体项目")
                sys.exit(1)
            success = updater.restore_to_checkpoint(matched_project, args.checkpoint)
            exit_code = 0 if success else 1
            
        elif args.action == "list-checkpoints":
            checkpoints = updater.list_available_checkpoints(matched_project)
            print("\n" + "=" * 60)
            print("可用的Git检查点")
            print("=" * 60)
            
            if checkpoints:
                if matched_project:
                    # 显示单个项目的检查点
                    print(f"\n📦 {matched_project}:")
                    for checkpoint_name, checkpoint_info in checkpoints.items():
                        timestamp = checkpoint_info.get("timestamp", "未知时间")
                        commit = checkpoint_info.get("commit_hash", "未知")[:8]
                        checkpoint_type = checkpoint_info.get("checkpoint_type", checkpoint_name)
                        print(f"  - {checkpoint_name}: {commit} ({timestamp})")
                        if checkpoint_info.get("description"):
                            print(f"    描述: {checkpoint_info['description']}")
                else:
                    # 显示所有项目的检查点
                    for project, project_checkpoints in checkpoints.items():
                        print(f"\n📦 {project}:")
                        for checkpoint_name, checkpoint_info in project_checkpoints.items():
                            timestamp = checkpoint_info.get("timestamp", "未知时间")
                            commit = checkpoint_info.get("commit_hash", "未知")[:8]
                            print(f"  - {checkpoint_name}: {commit} ({timestamp})")
            else:
                print("\n暂无可用检查点")
            print("\n" + "=" * 60)
            
        elif args.action == "cleanup":
            updater.cleanup_resources()
            print("✅ 资源清理完成")
            
        elif args.action == "export-config":
            updater.export_config_template()
            print("✅ 配置模板已导出")
        
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断操作")
        sys.exit(1)
    except Exception as e:
        # 统一通过日志系统处理错误
        if 'updater' in locals() and updater.logger:
            updater._log_safe("error", f"错误: {str(e)}")
            if args.debug:
                updater._log_safe("error", "调试信息:", exc_info=True)
        else:
            print(f"\n❌ 错误: {str(e)}")
            if args.debug:
                print("\n调试信息:")
                traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()