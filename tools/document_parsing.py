from typing import Any, Dict, List, Union
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin_dotsocr.client import DotsOCRClient
from dify_plugin_dotsocr.utils import bytes_to_image
import logging

# Configure logging
logger = logging.getLogger(__name__)

class DocumentParsingTool(Tool):
    def _invoke(self, tool_parameters: Dict[str, Any]) -> ToolInvokeMessage:
        """
        Run the document parsing tool
        """
        try:
            # Get settings from credentials (provider settings)
            # In the new SDK, credentials are passed in self.runtime.credentials
            settings = self.runtime.credentials
            
            client = DotsOCRClient(
                ip=settings.get('server_ip', '172.20.201.93'),
                port=int(settings.get('server_port', 8001)),
                protocol=settings.get('protocol', 'http'),
                model_name=settings.get('model_name', 'model'),
                timeout=int(settings.get('timeout', 300))
            )
            
            file_obj = tool_parameters.get('file')
            if not file_obj:
                return self.create_text_message("No file provided")

            prompt_mode = tool_parameters.get('prompt_mode', 'prompt_layout_all_en')
            max_concurrency = int(tool_parameters.get('max_concurrency', 20))

            # In the new SDK, file objects have 'extension' and 'content' (bytes)
            # Or they might be represented differently. Dify SDK usually provides 
            # the file content as bytes.
            file_content = file_obj.blob
            extension = file_obj.extension.lower() if hasattr(file_obj, 'extension') else ''
            
            if not extension:
                filename = file_obj.filename if hasattr(file_obj, 'filename') else ''
                if '.' in filename:
                    extension = filename.rsplit('.', 1)[1].lower()

            logger.info(f"Processing file with extension: {extension}, mode: {prompt_mode}")

            if extension == 'pdf':
                results = client.parse_pdf(file_content, prompt_mode, max_concurrency)
                return self.create_json_message({
                    "success": True,
                    "result": {
                        "pages": results,
                        "total_pages": len(results),
                        "mode": prompt_mode
                    }
                })
            elif extension in ['jpg', 'jpeg', 'png', 'tiff', 'tif', 'webp']:
                image = bytes_to_image(file_content)
                result = client.inference(image, prompt_mode)
                return self.create_json_message({
                    "success": True,
                    "result": {
                        "pages": [
                            {
                                "page": 1,
                                "content": result
                            }
                        ],
                        "total_pages": 1,
                        "mode": prompt_mode
                    }
                })
            else:
                return self.create_text_message(f"Unsupported file extension: {extension}. Supported: PDF, JPG, PNG, TIFF, WEBP")

        except Exception as e:
            logger.exception("Error during tool execution")
            return self.create_text_message(f"Error: {str(e)}")
