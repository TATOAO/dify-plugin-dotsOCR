import json
from typing import Any, Dict
from io import BytesIO
from PIL import Image

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin_dotsocr.client import DotsOCRClient

class DocumentParsingTool(Tool):
    def _invoke(self, tool_parameters: Dict[str, Any]) -> ToolInvokeMessage:
        file = tool_parameters.get('file')
        if not file:
            return self.create_text_message("Error: No file provided.")
        
        mode = tool_parameters.get('mode', 'prompt_layout_all_en')
        max_concurrency = int(tool_parameters.get('max_concurrency', 10))
        
        # Get credentials from provider configuration
        endpoint = self.runtime.credentials.get('endpoint')
        model_name = self.runtime.credentials.get('model_name', 'model')
        api_key = self.runtime.credentials.get('api_key', '0')
        
        if not endpoint:
            return self.create_text_message("Error: vLLM Endpoint not configured in provider settings.")
            
        client = DotsOCRClient(endpoint=endpoint, model_name=model_name, api_key=api_key)
        
        # Get file content
        file_content = file.blob
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
                return self.create_json_message(results)
            else:
                # Assume it's an image
                image = Image.open(BytesIO(file_content))
                result = client.inference(image, prompt_mode=mode)
                
                # Try to parse as JSON if possible, otherwise return as text
                try:
                    json_data = json.loads(result)
                    return self.create_json_message(json_data)
                except:
                    return self.create_text_message(result)
                    
        except Exception as e:
            return self.create_text_message(f"Error during parsing: {str(e)}")

