import os

class Config:
    def __init__(self, settings: dict):
        self.server_ip = settings.get('server_ip', '172.20.201.93')
        if not self.server_ip:
            raise ValueError("server_ip is required")
            
        try:
            self.server_port = int(settings.get('server_port', 8001))
        except (ValueError, TypeError):
            self.server_port = 8001
            
        self.protocol = settings.get('protocol', 'http')
        if self.protocol not in ['http', 'https']:
            self.protocol = 'http'
            
        self.model_name = settings.get('model_name', 'model')
        
        try:
            self.timeout = int(settings.get('timeout', 300))
        except (ValueError, TypeError):
            self.timeout = 300

    @property
    def base_url(self):
        return f"{self.protocol}://{self.server_ip}:{self.server_port}/v1"
