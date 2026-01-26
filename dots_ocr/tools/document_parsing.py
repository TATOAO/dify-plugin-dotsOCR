import json
from typing import Any, Dict, Generator
from io import BytesIO
from PIL import Image

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin_dotsocr.client import DotsOCRClient

class DocumentParsingTool(Tool):
    def _invoke(self, tool_parameters: Dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        file = tool_parameters.get('file')
        if not file:
            yield self.create_text_message("Error: No file provided.")
            return
        
        mode = tool_parameters.get('mode', 'prompt_layout_all_en')
        max_concurrency = int(tool_parameters.get('max_concurrency', 10))
        
        # Get credentials from provider configuration
        endpoint = self.runtime.credentials.get('endpoint')
        model_name = self.runtime.credentials.get('model_name', 'model')
        api_key = self.runtime.credentials.get('api_key', '0')
        
        if not endpoint:
            yield self.create_text_message("Error: vLLM Endpoint not configured in provider settings.")
            return
            
        client = DotsOCRClient(endpoint=endpoint, model_name=model_name, api_key=api_key)
        
        # Get file content
        # Try to get file content via blob first
        file_content = None
        try:
            file_content = file.blob
        except Exception as e:
            # If blob access fails, try to get file from URL
            import os
            import requests
            
            # Determine which URL to use based on transfer_method
            transfer_method = getattr(file, 'transfer_method', None)
            file_url = None
            
            # For local_file uploads, prefer remote_url, fallback to url
            # Both are typically relative paths that need FILES_URL prefix
            # For remote_url uploads, remote_url may already be absolute
            if transfer_method == 'local_file':
                # Prefer remote_url for local files, fallback to url
                file_url = getattr(file, 'remote_url', None) or getattr(file, 'url', None)
            elif transfer_method == 'remote_url':
                # For remote URLs, prefer remote_url (may be absolute), fallback to url
                file_url = getattr(file, 'remote_url', None) or getattr(file, 'url', None)
            else:
                # Fallback: try remote_url first, then url
                file_url = getattr(file, 'remote_url', None) or getattr(file, 'url', None)
            
            if not file_url:
                yield self.create_text_message(f"Error: Unable to access file blob and no URL available. Original error: {str(e)}. Please ensure the `FILES_URL` environment variable is set in your Dify environment.")
                return
            
            # Handle relative path - need to prepend FILES_URL
            if not file_url.startswith(('http://', 'https://')):
                # Try to get FILES_URL from environment variable
                files_url = os.environ.get('FILES_URL', '').rstrip('/')
                
                # Try to get from runtime if available (some Dify versions may provide this)
                if not files_url:
                    try:
                        files_url = getattr(self.runtime, 'files_url', None)
                        if files_url:
                            files_url = files_url.rstrip('/')
                    except:
                        pass
                
                if not files_url:
                    yield self.create_text_message(f"Error: Invalid file URL '{file_url}': Request URL is missing an 'http://' or 'https://' protocol. Please ensure the `FILES_URL` environment variable is set in your Dify environment (e.g., FILES_URL=http://your-dify-domain.com).")
                    return
                
                # Construct absolute URL
                file_url = f"{files_url}/{file_url.lstrip('/')}"
            
            # Download file from URL
            try:
                resp = requests.get(file_url, timeout=30)
                if resp.status_code == 200:
                    file_content = resp.content
                else:
                    yield self.create_text_message(f"Error: Failed to download file from {file_url} (Status {resp.status_code}). Please check Dify `FILES_URL` configuration.")
                    return
            except Exception as re:
                yield self.create_text_message(f"Error: Failed to download file from {file_url} ({str(re)}). Please check Dify `FILES_URL` configuration and network connectivity.")
                return
        
        if file_content is None:
            yield self.create_text_message("Error: Unable to retrieve file content. Please check file access permissions and Dify configuration.")
            return

        extension = file.extension.lower() if file.extension else ''
        if not extension:
            # Try to guess from mime_type if extension is not available
            mime_type = file.mime_type.lower() if file.mime_type else ''
            if 'pdf' in mime_type:
                extension = 'pdf'
            elif 'image' in mime_type:
                extension = 'png' # default image
        
        try:
            if extension == 'pdf':
                results = client.parse_pdf(file_content, prompt_mode=mode, max_concurrency=max_concurrency)
                yield self.create_json_message(results)
            else:
                # Assume it's an image
                image = Image.open(BytesIO(file_content))
                result = client.inference(image, prompt_mode=mode)
                
                # Try to parse as JSON if possible, otherwise return as text
                try:
                    json_data = json.loads(result)
                    yield self.create_json_message(json_data)
                except:
                    yield self.create_text_message(result)
                    
        except Exception as e:
            yield self.create_text_message(f"Error during parsing: {str(e)}")

