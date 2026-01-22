from typing import Any, Dict, List, Optional, Union
from dify_plugin_dotsocr.client import DotsOCRClient
from dify_plugin_dotsocr.config import Config
from dify_plugin_dotsocr.utils import bytes_to_image
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DotsOCRPlugin:
    def __init__(self):
        self.client = None

    def _init_client(self, settings: Dict[str, Any]):
        if not self.client:
            try:
                config = Config(settings)
                logger.info(f"Initializing DotsOCRClient with {config.base_url}")
                self.client = DotsOCRClient(
                    ip=config.server_ip,
                    port=config.server_port,
                    protocol=config.protocol,
                    model_name=config.model_name,
                    timeout=config.timeout
                )
            except Exception as e:
                logger.error(f"Failed to initialize DotsOCRClient: {str(e)}")
                raise

    def run(self, inputs: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the plugin tool
        """
        try:
            self._init_client(settings)
            
            file_obj = inputs.get('file')
            if not file_obj:
                return {"success": False, "error": "No file provided"}

            prompt_mode = inputs.get('prompt_mode', 'prompt_layout_all_en')
            max_concurrency = int(inputs.get('max_concurrency', 20))

            # In Dify, file objects usually have 'extension' and 'content' (bytes) or 'path'
            file_content = file_obj.get('content')
            if not file_content:
                return {"success": False, "error": "File content is empty"}
                
            extension = file_obj.get('extension', '').lower()
            if not extension:
                # Try to infer extension from filename if available
                filename = file_obj.get('filename', '')
                if '.' in filename:
                    extension = filename.rsplit('.', 1)[1].lower()

            logger.info(f"Processing file with extension: {extension}, mode: {prompt_mode}")

            if extension == 'pdf':
                results = self.client.parse_pdf(file_content, prompt_mode, max_concurrency)
                return {
                    "success": True,
                    "result": {
                        "pages": results,
                        "total_pages": len(results),
                        "mode": prompt_mode
                    }
                }
            elif extension in ['jpg', 'jpeg', 'png', 'tiff', 'tif', 'webp']:
                image = bytes_to_image(file_content)
                result = self.client.inference(image, prompt_mode)
                return {
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
                }
            else:
                return {"success": False, "error": f"Unsupported file extension: {extension}. Supported: PDF, JPG, PNG, TIFF, WEBP"}

        except Exception as e:
            logger.exception("Error during plugin execution")
            return {"success": False, "error": str(e)}
