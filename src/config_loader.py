# Databricks notebook source
"""
Configuration Loader - Load and parse YAML configurations
"""

import yaml
from typing import Dict, Any, List, Optional


class ConfigLoader:
    """Load and manage pipeline configurations"""
    
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.connections = {}
        self.pipelines = []
        
    def load_connections(self, config_path: str = "config/connections.yml") -> Dict[str, Any]:
        """Load database connections configuration"""
        full_path = f"/Workspace{self.workspace_path}/{config_path}"
        
        with open(full_path, 'r') as file:
            config = yaml.safe_load(file)
            self.connections = config.get('connections', {})
        
        return self.connections
    
    def load_pipelines(self, config_path: str = "config/pipelines.yml") -> List[Dict[str, Any]]:
        """Load pipeline configurations"""
        full_path = f"/Workspace{self.workspace_path}/{config_path}"
        
        with open(full_path, 'r') as file:
            config = yaml.safe_load(file)
            self.pipelines = config.get('pipelines', [])
        
        return self.pipelines
    
    def get_connection(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get specific connection configuration"""
        return self.connections.get(connection_id)
    
    def get_pipeline(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get specific pipeline configuration"""
        for pipeline in self.pipelines:
            if pipeline.get('pipeline_id') == pipeline_id:
                return pipeline
        return None
    
    def get_enabled_pipelines(self) -> List[Dict[str, Any]]:
        """Get all enabled pipelines"""
        return [p for p in self.pipelines if p.get('enabled', True)]
    
    def validate_pipeline(self, pipeline: Dict[str, Any]) -> tuple[bool, str]:
        """Validate pipeline configuration"""
        required_fields = ['pipeline_id', 'source', 'target', 'sync_config']
        
        for field in required_fields:
            if field not in pipeline:
                return False, f"Missing required field: {field}"
        
        # Validate source connection exists
        source_conn = pipeline['source'].get('connection')
        if source_conn and source_conn not in self.connections:
            return False, f"Source connection not found: {source_conn}"
        
        # Validate target connection exists
        target_conn = pipeline['target'].get('connection')
        if target_conn and target_conn not in self.connections:
            return False, f"Target connection not found: {target_conn}"
        
        return True, "Valid"
    
    def substitute_variables(self, config: Dict[str, Any], variables: Dict[str, str]) -> Dict[str, Any]:
        """Substitute environment variables in configuration"""
        import json
        import re
        
        # Convert to JSON string for easy substitution
        config_str = json.dumps(config)
        
        # Replace ${var} patterns
        for key, value in variables.items():
            pattern = r'\$\{' + key + r'\}'
            config_str = re.sub(pattern, value, config_str)
        
        return json.loads(config_str)
