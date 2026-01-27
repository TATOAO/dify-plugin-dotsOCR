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
        files_url_from_config = self.runtime.credentials.get('files_url', '').strip()
        
        if not endpoint:
            yield self.create_text_message("Error: vLLM Endpoint not configured in provider settings.")
            return
        
        # Set timeout to match MAX_REQUEST_TIMEOUT (300 seconds)
        # This ensures the client timeout matches the plugin timeout
        timeout = 300
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
                yield self.create_text_message(f"Error: Unable to access file blob and no URL available. Original error: {str(e)}. Please ensure the `FILES_URL` environment variable is set in your Dify environment.")
                return
            
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
                    yield self.create_text_message(f"Error: Invalid file URL '{file_url}': Request URL is missing an 'http://' or 'https://' protocol. Please configure 'Dify Files URL' in the plugin settings, or set the `FILES_URL` environment variable in your Dify environment (e.g., FILES_URL=http://your-dify-domain.com).")
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
        # Remove leading dot if present (e.g., ".pdf" -> "pdf")
        extension = extension.lstrip('.') if extension else ''
        if not extension:
            # Try to guess from mime_type if extension is not available
            mime_type = file.mime_type.lower() if file.mime_type else ''
            if 'pdf' in mime_type:
                extension = 'pdf'
            elif 'image' in mime_type:
                extension = 'png' # default image
        
        try:
            if extension == 'pdf':
                # Send progress message
                yield self.create_text_message("Starting PDF parsing...")
                
                results = client.parse_pdf(file_content, prompt_mode=mode, max_concurrency=max_concurrency)
                
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
                        yield self.create_text_message("Error: No results returned from PDF parsing.")
                        return
                    
                    # Try to serialize to JSON string to ensure data integrity
                    try:
                        json_str = json.dumps(results, indent=2, ensure_ascii=False)
                    except Exception as e:
                        yield self.create_text_message(f"Error: JSON serialization failed: {str(e)}")
                        return

                    # CRITICAL: For large results, the plugin framework's JSON message often becomes {} 
                    # causing an AssertionError in Dify. We will output the JSON string as text 
                    # if it's large, which is much more stable in Dify.
                    
                    if len(json_str) > 30 * 1024:  # > 30KB
                        yield self.create_text_message("Note: Result is large, returning as formatted JSON text to ensure stability.")
                        yield self.create_text_message(json_str)
                    else:
                        try:
                            # For small results, try actual JSON message first
                            # MUST wrap in a dict, Dify create_json_message doesn't like lists
                            yield self.create_json_message({"pages": results})
                        except Exception:
                            # Fallback to text message
                            yield self.create_text_message(json_str)
                    
                except Exception as delivery_e:
                    yield self.create_text_message(f"Error during result delivery: {str(delivery_e)}")
            
            else:
                # Assume it's an image
                yield self.create_text_message("Starting image parsing...")
                
                image = Image.open(BytesIO(file_content))
                result = client.inference(image, prompt_mode=mode)
                
                # Try to parse as JSON string to ensure stability
                if result:
                    if len(result) > 30 * 1024:
                        yield self.create_text_message(result)
                    else:
                        try:
                            # Try to parse as JSON first
                            json_data = json.loads(result)
                            # Wrap in a dict for stability
                            if isinstance(json_data, dict):
                                yield self.create_json_message(json_data)
                            else:
                                yield self.create_json_message({"result": json_data})
                        except Exception:
                            # Fallback to text
                            yield self.create_text_message(result)
                else:
                    yield self.create_text_message("Error: Empty result from image parsing.")
                    
        except KeyboardInterrupt:
            yield self.create_text_message("Error: Parsing was interrupted by user.")
        except Exception as e:
            # Provide more detailed error information
            import traceback
            error_traceback = traceback.format_exc()
            error_msg = str(e)
            error_type = type(e).__name__
            
            # Try to get more context about the error
            try:
                # Check if client exists
                client_info = f"Client timeout: {client.timeout}s" if 'client' in locals() else "Client not initialized"
            except:
                client_info = "Unable to get client info"
            
            # Include full traceback in error message for debugging
            full_error = f"Error type: {error_type}\nError message: {error_msg}\n{client_info}\n\nTraceback:\n{error_traceback}"
            
            # Format error message based on error type
            if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                formatted_error = f"Request timeout: The dots_ocr service took longer than {client.timeout if 'client' in locals() else 300} seconds to respond. This may indicate the service is overloaded or the document is too complex.\n\nError details: {error_msg}"
            elif "json" in error_msg.lower() or "serialization" in error_msg.lower():
                formatted_error = f"JSON serialization error: {error_msg}\n\nThis may indicate the response from dots_ocr is too large or contains invalid data."
            elif "connection" in error_msg.lower() or "network" in error_msg.lower():
                formatted_error = f"Network error: {error_msg}\n\nPlease check the dots_ocr service endpoint and network connectivity."
            else:
                formatted_error = f"Error during parsing: {error_msg}"
            
            # Send error message (ensure it's not too long for Dify)
            # Dify may have limits on message length, so we'll keep it reasonable
            max_error_length = 3000
            if len(full_error) > max_error_length:
                error_to_send = f"{formatted_error}\n\nFull error details (truncated):\n{full_error[:max_error_length]}..."
            else:
                error_to_send = f"{formatted_error}\n\nFull error details:\n{full_error}"
            
            try:
                yield self.create_text_message(error_to_send)
            except Exception as yield_error:
                # If even yielding the error fails, try a minimal error message
                try:
                    yield self.create_text_message(f"Critical error: {error_type}: {error_msg[:500]}")
                except:
                    # Last resort - this shouldn't happen but if it does, at least we tried
                    pass

