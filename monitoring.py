"""
Monitoring and logging system for Nexus AI Assistant.

This module provides enhanced monitoring, logging, and observability features.
"""

import os
import sys
import time
import logging
import json
import traceback
import threading
import socket
import platform
import psutil
from typing import Dict, Any, List, Optional, Union, Callable
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import prometheus_client
from prometheus_client import Counter, Gauge, Histogram, Summary
from prometheus_client.exposition import start_http_server

# Configure default logger
logger = logging.getLogger(__name__)

class NexusLogger:
    """Enhanced logger for Nexus AI Assistant."""
    
    def __init__(self, config=None):
        """Initialize logger.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.log_level = self._get_config('LOG_LEVEL', 'INFO')
        self.log_format = self._get_config('LOG_FORMAT', 
                                          '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.log_dir = self._get_config('LOG_DIR', 'logs')
        self.log_file = self._get_config('LOG_FILE', 'nexus.log')
        self.max_bytes = self._get_config('LOG_MAX_BYTES', 10 * 1024 * 1024)  # 10 MB
        self.backup_count = self._get_config('LOG_BACKUP_COUNT', 5)
        self.log_to_console = self._get_config('LOG_TO_CONSOLE', True)
        self.log_to_file = self._get_config('LOG_TO_FILE', True)
        self.json_logging = self._get_config('JSON_LOGGING', False)
        
        # Create logger
        self.logger = logging.getLogger('nexus')
        self.logger.setLevel(self._get_log_level())
        
        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Add handlers
        if self.log_to_console:
            self._add_console_handler()
        
        if self.log_to_file:
            self._add_file_handler()
    
    def _get_config(self, key, default=None):
        """Get configuration value.
        
        Args:
            key: Configuration key
            default: Default value
            
        Returns:
            Configuration value
        """
        return self.config.get(key, default)
    
    def _get_log_level(self):
        """Get log level.
        
        Returns:
            Log level
        """
        levels = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        return levels.get(self.log_level.upper(), logging.INFO)
    
    def _add_console_handler(self):
        """Add console handler to logger."""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self._get_log_level())
        
        if self.json_logging:
            formatter = self._create_json_formatter()
        else:
            formatter = logging.Formatter(self.log_format)
        
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
    
    def _add_file_handler(self):
        """Add file handler to logger."""
        # Create log directory if it doesn't exist
        log_path = Path(self.log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # Create file handler
        log_file_path = log_path / self.log_file
        file_handler = RotatingFileHandler(
            log_file_path,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count
        )
        file_handler.setLevel(self._get_log_level())
        
        if self.json_logging:
            formatter = self._create_json_formatter()
        else:
            formatter = logging.Formatter(self.log_format)
        
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
    
    def _create_json_formatter(self):
        """Create JSON formatter.
        
        Returns:
            JSON formatter
        """
        return JsonFormatter()
    
    def get_logger(self):
        """Get logger instance.
        
        Returns:
            Logger instance
        """
        return self.logger

class JsonFormatter(logging.Formatter):
    """JSON formatter for logging."""
    
    def format(self, record):
        """Format log record as JSON.
        
        Args:
            record: Log record
            
        Returns:
            Formatted JSON string
        """
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'name': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread': record.threadName,
            'process': record.processName
        }
        
        # Add exception info if available
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        return json.dumps(log_data)

class NexusMonitoring:
    """Monitoring system for Nexus AI Assistant."""
    
    def __init__(self, config=None):
        """Initialize monitoring system.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.enabled = self._get_config('MONITORING_ENABLED', True)
        self.port = self._get_config('PROMETHEUS_PORT', 9090)
        self.metrics_path = self._get_config('METRICS_PATH', '/metrics')
        self.collect_interval = self._get_config('COLLECT_INTERVAL', 15)  # seconds
        self.system_metrics_enabled = self._get_config('SYSTEM_METRICS_ENABLED', True)
        
        # Initialize metrics
        self.metrics = {}
        self._initialize_metrics()
        
        # Start metrics server if enabled
        if self.enabled:
            self._start_metrics_server()
            
            # Start system metrics collection if enabled
            if self.system_metrics_enabled:
                self._start_system_metrics_collection()
    
    def _get_config(self, key, default=None):
        """Get configuration value.
        
        Args:
            key: Configuration key
            default: Default value
            
        Returns:
            Configuration value
        """
        return self.config.get(key, default)
    
    def _initialize_metrics(self):
        """Initialize metrics."""
        # Request metrics
        self.metrics['request_count'] = Counter(
            'nexus_request_count',
            'Number of requests received',
            ['endpoint', 'method', 'status']
        )
        
        self.metrics['request_latency'] = Histogram(
            'nexus_request_latency_seconds',
            'Request latency in seconds',
            ['endpoint', 'method'],
            buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10)
        )
        
        # System metrics
        self.metrics['cpu_usage'] = Gauge(
            'nexus_cpu_usage_percent',
            'CPU usage percentage'
        )
        
        self.metrics['memory_usage'] = Gauge(
            'nexus_memory_usage_bytes',
            'Memory usage in bytes'
        )
        
        self.metrics['memory_percent'] = Gauge(
            'nexus_memory_usage_percent',
            'Memory usage percentage'
        )
        
        self.metrics['disk_usage'] = Gauge(
            'nexus_disk_usage_bytes',
            'Disk usage in bytes',
            ['mountpoint', 'type']
        )
        
        self.metrics['disk_percent'] = Gauge(
            'nexus_disk_usage_percent',
            'Disk usage percentage',
            ['mountpoint']
        )
        
        # Application metrics
        self.metrics['active_sessions'] = Gauge(
            'nexus_active_sessions',
            'Number of active sessions'
        )
        
        self.metrics['plugin_count'] = Gauge(
            'nexus_plugin_count',
            'Number of loaded plugins'
        )
        
        self.metrics['model_latency'] = Histogram(
            'nexus_model_latency_seconds',
            'Model inference latency in seconds',
            ['model_name'],
            buckets=(0.1, 0.5, 1, 2, 5, 10, 20, 30, 60)
        )
    
    def _start_metrics_server(self):
        """Start Prometheus metrics server."""
        try:
            start_http_server(self.port)
            logger.info(f"Started Prometheus metrics server on port {self.port}")
        except Exception as e:
            logger.error(f"Failed to start Prometheus metrics server: {str(e)}")
    
    def _start_system_metrics_collection(self):
        """Start system metrics collection."""
        def collect_system_metrics():
            while True:
                try:
                    # Collect CPU metrics
                    cpu_percent = psutil.cpu_percent(interval=1)
                    self.metrics['cpu_usage'].set(cpu_percent)
                    
                    # Collect memory metrics
                    memory = psutil.virtual_memory()
                    self.metrics['memory_usage'].set(memory.used)
                    self.metrics['memory_percent'].set(memory.percent)
                    
                    # Collect disk metrics
                    for partition in psutil.disk_partitions():
                        try:
                            usage = psutil.disk_usage(partition.mountpoint)
                            self.metrics['disk_usage'].labels(
                                mountpoint=partition.mountpoint,
                                type=partition.fstype
                            ).set(usage.used)
                            
                            self.metrics['disk_percent'].labels(
                                mountpoint=partition.mountpoint
                            ).set(usage.percent)
                        except (PermissionError, FileNotFoundError):
                            # Skip partitions that can't be accessed
                            pass
                except Exception as e:
                    logger.error(f"Error collecting system metrics: {str(e)}")
                
                time.sleep(self.collect_interval)
        
        # Start collection thread
        thread = threading.Thread(target=collect_system_metrics, daemon=True)
        thread.start()
        logger.info("Started system metrics collection")
    
    def track_request(self, endpoint, method, status, latency):
        """Track HTTP request.
        
        Args:
            endpoint: Request endpoint
            method: HTTP method
            status: HTTP status code
            latency: Request latency in seconds
        """
        if not self.enabled:
            return
            
        self.metrics['request_count'].labels(
            endpoint=endpoint,
            method=method,
            status=status
        ).inc()
        
        self.metrics['request_latency'].labels(
            endpoint=endpoint,
            method=method
        ).observe(latency)
    
    def track_model_latency(self, model_name, latency):
        """Track model inference latency.
        
        Args:
            model_name: Model name
            latency: Inference latency in seconds
        """
        if not self.enabled:
            return
            
        self.metrics['model_latency'].labels(
            model_name=model_name
        ).observe(latency)
    
    def set_active_sessions(self, count):
        """Set number of active sessions.
        
        Args:
            count: Number of active sessions
        """
        if not self.enabled:
            return
            
        self.metrics['active_sessions'].set(count)
    
    def set_plugin_count(self, count):
        """Set number of loaded plugins.
        
        Args:
            count: Number of loaded plugins
        """
        if not self.enabled:
            return
            
        self.metrics['plugin_count'].set(count)
    
    def get_system_stats(self):
        """Get system statistics.
        
        Returns:
            System statistics
        """
        stats = {
            'cpu': {
                'percent': psutil.cpu_percent(interval=0.1),
                'count': psutil.cpu_count(),
                'load': [x / psutil.cpu_count() * 100 for x in psutil.getloadavg()]
            },
            'memory': {
                'total': psutil.virtual_memory().total,
                'available': psutil.virtual_memory().available,
                'used': psutil.virtual_memory().used,
                'percent': psutil.virtual_memory().percent
            },
            'disk': {
                'total': psutil.disk_usage('/').total,
                'used': psutil.disk_usage('/').used,
                'free': psutil.disk_usage('/').free,
                'percent': psutil.disk_usage('/').percent
            },
            'network': {
                'hostname': socket.gethostname(),
                'ip': socket.gethostbyname(socket.gethostname())
            },
            'platform': {
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'python': platform.python_version()
            }
        }
        
        # Add GPU stats if available
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            stats['gpu'] = [
                {
                    'id': gpu.id,
                    'name': gpu.name,
                    'load': gpu.load * 100,
                    'memory': {
                        'total': gpu.memoryTotal,
                        'used': gpu.memoryUsed,
                        'free': gpu.memoryFree,
                        'percent': gpu.memoryUtil * 100
                    },
                    'temperature': gpu.temperature
                }
                for gpu in gpus
            ]
        except (ImportError, Exception):
            # GPU monitoring not available
            pass
        
        return stats

class HealthCheck:
    """Health check system for Nexus AI Assistant."""
    
    def __init__(self, config=None):
        """Initialize health check system.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.checks = {}
        self.register_default_checks()
    
    def register_check(self, name, check_func, description=None):
        """Register health check.
        
        Args:
            name: Check name
            check_func: Check function
            description: Check description
        """
        self.checks[name] = {
            'func': check_func,
            'description': description or name,
            'status': 'unknown',
            'message': None,
            'last_check': None
        }
    
    def register_default_checks(self):
        """Register default health checks."""
        # CPU check
        self.register_check(
            'cpu',
            lambda: self._check_cpu_usage(threshold=90),
            'CPU usage check'
        )
        
        # Memory check
        self.register_check(
            'memory',
            lambda: self._check_memory_usage(threshold=90),
            'Memory usage check'
        )
        
        # Disk check
        self.register_check(
            'disk',
            lambda: self._check_disk_usage(threshold=90),
            'Disk usage check'
        )
    
    def _check_cpu_usage(self, threshold=90):
      <response clipped><NOTE>To save on context only part of this file has been shown to you. You should retry this tool after you have searched inside the file with `grep -n` in order to find the line numbers of what you are looking for.</NOTE>