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
            raise ValueError("No file provided.")
        
        mode = tool_parameters.get('mode', 'prompt_layout_all_en')
        max_concurrency = int(tool_parameters.get('max_concurrency', 10))
        
        # Get credentials from provider configuration
        endpoint = self.runtime.credentials.get('endpoint')
        model_name = self.runtime.credentials.get('model_name', 'model')
        api_key = self.runtime.credentials.get('api_key', '0')
        files_url_from_config = self.runtime.credentials.get('files_url', '').strip()
        pdf_service_url = self.runtime.credentials.get('pdf_service_url', '').strip()

        if not endpoint:
            raise ValueError("vLLM Endpoint not configured in provider settings.")
        
        timeout = 3600
        client = DotsOCRClient(endpoint=endpoint, model_name=model_name, api_key=api_key, timeout=timeout)
        
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
                raise ValueError(f"Unable to access file blob and no URL available. Original error: {str(e)}. Please ensure the `FILES_URL` environment variable is set in your Dify environment.")
            
            # Handle relative path - need to prepend FILES_URL
            if not file_url.startswith(('http://', 'https://')):
                # Try to get FILES_URL in priority order:
                # 1. From plugin configuration (highest priority)
                # 2. From environment variable
                # 3. From runtime attributes
                files_url = None
                
                # Priority 1: From plugin configuration
                if files_url_from_config:
                    files_url = files_url_from_config.rstrip('/')
                
                # Priority 2: From environment variable
                if not files_url:
                    files_url = os.environ.get('FILES_URL', '').rstrip('/')
                
                # Priority 3: Try to get from runtime if available (some Dify versions may provide this)
                if not files_url:
                    try:
                        # Try different possible attribute names
                        files_url = getattr(self.runtime, 'files_url', None)
                        if not files_url:
                            files_url = getattr(self.runtime, 'FILES_URL', None)
                        if not files_url:
                            # Try to get from runtime.config or runtime.settings
                            if hasattr(self.runtime, 'config'):
                                files_url = getattr(self.runtime.config, 'files_url', None) or getattr(self.runtime.config, 'FILES_URL', None)
                        if files_url:
                            files_url = str(files_url).rstrip('/')
                    except Exception as runtime_error:
                        # Silently continue if runtime doesn't have files_url
                        pass
                
                if not files_url:
                    raise ValueError(f"Invalid file URL '{file_url}': Request URL is missing an 'http://' or 'https://' protocol. Please configure 'Dify Files URL' in the plugin settings, or set the `FILES_URL` environment variable in your Dify environment (e.g., FILES_URL=http://your-dify-domain.com).")
                
                # Construct absolute URL
                file_url = f"{files_url}/{file_url.lstrip('/')}"
            
            # Download file from URL
            try:
                resp = requests.get(file_url, timeout=100)
                if resp.status_code == 200:
                    file_content = resp.content
                else:
                    raise RuntimeError(f"Failed to download file from {file_url} (Status {resp.status_code}). Please check Dify `FILES_URL` configuration.")
            except RuntimeError:
                raise
            except Exception as re:
                raise RuntimeError(f"Failed to download file from {file_url} ({str(re)}). Please check Dify `FILES_URL` configuration and network connectivity.")
        
        if file_content is None:
            raise ValueError("Unable to retrieve file content. Please check file access permissions and Dify configuration.")

        extension = file.extension.lower() if file.extension else ''
        # Remove leading dot if present (e.g., ".pdf" -> "pdf")
        extension = extension.lstrip('.') if extension else ''
        if not extension:
            # Try to guess from mime_type if extension is not available
            mime_type = file.mime_type.lower() if file.mime_type else ''
            if 'pdf' in mime_type:
                extension = 'pdf'
            elif 'word' in mime_type or 'msword' in mime_type or 'officedocument' in mime_type:
                extension = 'docx'
            elif 'image' in mime_type:
                extension = 'png' # default image

        # Handle Word files: convert to PDF first
        if extension in ('doc', 'docx'):
            if not pdf_service_url:
                raise ValueError(
                    "Word 文件（.doc/.docx）需要配置 'Word to PDF Service URL' 才能解析。"
                    "请在插件设置中配置 'Word to PDF Service URL'（例如：http://localhost:31234/convert）。\n\n"
                    "Word files (.doc/.docx) require 'Word to PDF Service URL' to be configured. "
                    "Please set 'Word to PDF Service URL' in the plugin provider settings (e.g., http://localhost:31234/convert)."
                )

            yield self.create_text_message("Converting Word document to PDF...")
            try:
                import requests as req
                filename = getattr(file, 'filename', None) or f"document.{extension}"
                resp = req.post(
                    pdf_service_url,
                    files={"file": (filename, file_content)},
                    timeout=120,
                )
                if resp.status_code == 200:
                    file_content = resp.content
                    extension = 'pdf'
                else:
                    raise RuntimeError(
                        f"Word 转 PDF 失败，服务返回状态码 {resp.status_code}。"
                        f"请检查 Word to PDF 服务是否正常运行（{pdf_service_url}）。"
                    )
            except RuntimeError:
                raise
            except Exception as convert_e:
                raise RuntimeError(
                    f"Word 转 PDF 失败：{str(convert_e)}。"
                    f"请检查 Word to PDF 服务是否正常运行（{pdf_service_url}）。"
                )

        try:
            if extension == 'pdf':
                # Send progress message
                yield self.create_text_message(f"Starting PDF parsing with max_concurrency={max_concurrency}...")
                
                results = []
                # parse_pdf is now a generator that yields progress strings and finally the results list
                for item in client.parse_pdf(file_content, prompt_mode=mode, max_concurrency=max_concurrency):
                    if isinstance(item, str):
                        yield self.create_text_message(item)
                    elif isinstance(item, list):
                        results = item
                
                if not results:
                    raise RuntimeError("No results returned from PDF parsing.")
                
                # Check if any page had errors
                error_pages = [r for r in results if isinstance(r.get('content'), str) and r.get('content', '').startswith('Error:')]
                if error_pages:
                    page_nums = [str(r['page']) for r in error_pages]
                    error_info = f"Some pages failed: {', '.join(['Page ' + p for p in page_nums])}"
                    yield self.create_text_message(f"Warning: {error_info}. Partial results:")
                
                # Validate and serialize results before sending
                try:
                    # Ensure results is not empty
                    if not results:
                        raise RuntimeError("No results returned from PDF parsing.")
                    
                    # Extract full text from all pages
                    full_text_parts = []
                    for page_result in results:
                        content = page_result.get('content', '')
                        if not content:
                            continue
                            
                        if isinstance(content, str):
                            content_str = content.strip()
                            if not content_str:
                                continue
                            try:
                                # Try to parse as JSON if it looks like it (JSON list or object)
                                if content_str.startswith(('[', '{')):
                                    elements = json.loads(content_str)
                                    if isinstance(elements, list):
                                        for element in elements:
                                            text = element.get('text', '')
                                            if text:
                                                full_text_parts.append(str(text))
                                    elif isinstance(elements, dict):
                                        text = elements.get('text', '')
                                        if text:
                                            full_text_parts.append(str(text))
                                        else:
                                            # If it's a dict but no text field, use the whole thing as string
                                            full_text_parts.append(content_str)
                                    else:
                                        full_text_parts.append(content_str)
                                else:
                                    # Not JSON, just plain text (e.g. from prompt_ocr)
                                    full_text_parts.append(content_str)
                            except Exception:
                                # If JSON parsing fails, use as plain text
                                full_text_parts.append(content_str)
                        elif isinstance(content, (list, dict)):
                            # Already parsed JSON
                            if isinstance(content, list):
                                for element in content:
                                    if isinstance(element, dict) and 'text' in element:
                                        full_text_parts.append(str(element['text']))
                            elif isinstance(content, dict):
                                if 'text' in content:
                                    full_text_parts.append(str(content['text']))
                    
                    full_text = "\n\n".join(full_text_parts)
                    
                    # Construct output data matching output_schema
                    result_object = {
                        "full_text": full_text,
                        "pages": results
                    }

                    # Use create_variable_message to explicitly fill output variables
                    # as suggested by Dify plugin development best practices
                    try:
                        yield self.create_variable_message("full_text", full_text)
                        yield self.create_variable_message("pages", results)
                        yield self.create_variable_message("result", result_object)
                    except Exception as e:
                        # Fallback: try to send at least the full_text if complex types fail
                        try:
                            yield self.create_variable_message("full_text", full_text)
                        except:
                            # Last resort: send as text
                            yield self.create_text_message(json.dumps(result_object, ensure_ascii=False))
                    
                except Exception as delivery_e:
                    yield self.create_text_message(f"Error during result delivery: {str(delivery_e)}")
            
            else:
                # Assume it's an image
                yield self.create_text_message("Starting image parsing...")
                
                image = Image.open(BytesIO(file_content))
                result = client.inference(image, prompt_mode=mode)
                
                # Process result
                if result:
                    try:
                        # Try to parse as JSON first
                        content_str = result.strip()
                        full_text = ""
                        json_data = None
                        
                        if content_str.startswith(('[', '{')):
                            try:
                                json_data = json.loads(content_str)
                                if isinstance(json_data, list):
                                    full_text = "\n\n".join([str(item.get('text', '')) for item in json_data if isinstance(item, dict) and item.get('text')])
                                elif isinstance(json_data, dict):
                                    full_text = str(json_data.get('text', ''))
                                    if not full_text and 'data' in json_data:
                                        full_text = str(json_data['data'])
                            except:
                                full_text = content_str
                        else:
                            full_text = content_str
                        
                        # Prepare standardized output data
                        # For images, we create a single-page list for consistency
                        image_results = [{
                            "page": 1,
                            "content": result
                        }]
                        
                        result_object = json_data if isinstance(json_data, (dict, list)) else {"raw_result": result}
                        
                        # Use create_variable_message to explicitly fill output variables
                        yield self.create_variable_message("full_text", full_text)
                        yield self.create_variable_message("pages", image_results)
                        yield self.create_variable_message("result", result_object)
                        
                    except Exception as e:
                        # Fallback
                        yield self.create_variable_message("full_text", result)
                        yield self.create_variable_message("result", {"raw_result": result, "error": str(e)})
                else:
                    raise RuntimeError("Empty result from image parsing.")
                    
        except KeyboardInterrupt:
            raise
        except Exception as e:
            # Re-raise so Dify marks the workflow as failed
            raise

