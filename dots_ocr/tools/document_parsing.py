from typing import Any, Dict
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

class DocumentParsingTool(Tool):
    def _invoke(self, tool_parameters: Dict[str, Any]) -> ToolInvokeMessage:
        return self.create_text_message("Hello World! This is a minimized version of the Dots.OCR plugin.")
