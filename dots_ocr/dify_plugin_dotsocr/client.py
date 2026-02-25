import base64
import json
import os
import requests
from io import BytesIO
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
import fitz  # PyMuPDF

class DotsOCRClient:
    def __init__(self, endpoint: str, model_name: str = 'model', api_key: str = '0', timeout: int = 3600):
        """
        Initialize dots.ocr client
        :param endpoint: vLLM server endpoint (e.g. http://172.20.201.93:8001/v1)
        :param model_name: Model name (default 'model')
        :param api_key: API key (default '0')
        :param timeout: Request timeout in seconds (default 3600)
        """
        self.endpoint = endpoint.rstrip('/')
        self.model_name = model_name
        self.timeout = timeout
        # Set timeout for OpenAI client - this is critical for long-running requests
        self.client = OpenAI(
            api_key=api_key, 
            base_url=self.endpoint,
            timeout=timeout
        )
        
    def image_to_base64(self, image):
        """Convert PIL Image to base64 string"""
        buffered = BytesIO()
        if image.mode != 'RGB':
            image = image.convert('RGB')
        image.save(buffered, format="JPEG")
        return f"data:image/jpeg;base64,{base64.b64encode(buffered.getvalue()).decode('utf-8')}"

    def _get_prompt(self, mode):
        """
        Get specific Prompt for dots.ocr
        """
        prompts = {
            "prompt_layout_all_en": """Please output the layout information from the PDF image, including each layout element's bbox, its category, and the corresponding text content within the bbox. 
1. Bbox format: [x1, y1, x2, y2] 
2. Layout Categories: The possible categories are ['Caption', 'Footnote', 'Formula', 'List-item', 'Page-footer', 'Page-header', 'Picture', 'Section-header', 'Table', 'Text', 'Title']. 
3. Text Extraction & Formatting Rules: 
- Picture: For the 'Picture' category, the text field should be omitted. 
- Formula: Format its text as LaTeX. 
- Table: Format its text as HTML. 
- All Others (Text, Title, etc.): Format their text as Markdown. 
4. Constraints: 
- The output text must be the original text from the image, with no translation. 
- All layout elements must be sorted according to human reading order. 
5. Final Output: The entire output must be a single JSON object. """,
            "prompt_layout_only_en": """Please output the layout information from this PDF image, including each layout's bbox and its category. The bbox should be in the format [x1, y1, x2, y2]. The layout categories for the PDF document include ['Caption', 'Footnote', 'Formula', 'List-item', 'Page-footer', 'Page-header', 'Picture', 'Section-header', 'Table', 'Text', 'Title']. Do not output the corresponding text. The layout result should be in JSON format.""",
            "prompt_ocr": "Extract the text content from this image."
        }
        return prompts.get(mode, prompts["prompt_layout_all_en"])

    def inference(self, image, prompt_mode="prompt_layout_all_en"):
        """
        Inference on a single image
        """
        try:
            prompt = self._get_prompt(prompt_mode)
            base64_image = self.image_to_base64(image)
            
            # vLLM needs specific prompt prefix to identify images
            full_prompt = f"<|img|><|imgpad|><|endofimg|>{prompt}"
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": base64_image}},
                            {"type": "text", "text": full_prompt},
                        ],
                    }
                ],
                temperature=0.1,
                top_p=0.9,
                max_completion_tokens=16384,
                timeout=self.timeout,
            )
            
            if not response or not response.choices:
                raise ValueError("Empty response from dots_ocr service")
            
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty content in response from dots_ocr service")
            
            return content
        except Exception as e:
            # Re-raise with more context
            error_msg = f"Error during inference: {str(e)}"
            if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                error_msg += f" (Request timed out after {self.timeout} seconds)"
            raise Exception(error_msg) from e

    def parse_pdf(self, pdf_stream: bytes, prompt_mode="prompt_layout_all_en", max_concurrency=20):
        """
        Parse PDF file (parallel call to dots.ocr)
        Yields progress messages and finally the results
        """
        try:
            doc = fitz.open(stream=pdf_stream, filetype="pdf")
            total_pages = len(doc)
            pages_to_process = []
            
            yield f"Extracting {total_pages} pages from PDF..."
            for page_num in range(total_pages):
                page = doc[page_num]
                pix = page.get_pixmap(dpi=200)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                pages_to_process.append((page_num + 1, img))
            
            doc.close()
            
            results_map = {}
            completed_count = 0
            
            yield f"Starting parallel processing with {max_concurrency} workers..."
            
            def process_page(page_info):
                page_num, img = page_info
                try:
                    output = self.inference(img, prompt_mode)
                    return page_num, output, None
                except Exception as exc:
                    # Return error instead of raising
                    error_msg = str(exc)
                    if "timeout" in error_msg.lower():
                        error_msg = f"Timeout error on page {page_num}: Request exceeded {self.timeout} seconds"
                    return page_num, None, f"Error: {error_msg}"

            with ThreadPoolExecutor(max_workers=max_concurrency) as executor:
                future_to_page = {executor.submit(process_page, page): page[0] for page in pages_to_process}
                for future in as_completed(future_to_page):
                    page_num = future_to_page[future]
                    try:
                        p_num, content, error = future.result()
                        if error:
                            results_map[p_num] = error
                            yield f"Page {p_num} failed: {error}"
                        else:
                            results_map[p_num] = content
                            yield f"Page {p_num} completed ({completed_count + 1}/{total_pages})"
                        completed_count += 1
                        
                    except Exception as exc:
                        # Store detailed error information
                        error_msg = str(exc)
                        if "timeout" in error_msg.lower():
                            error_msg = f"Timeout error on page {page_num}: Request exceeded {self.timeout} seconds"
                        results_map[page_num] = f"Error: {error_msg}"
                        completed_count += 1
                        yield f"Page {page_num} critical error: {error_msg}"

            final_results = []
            for p_num in sorted(results_map.keys()):
                final_results.append({
                    "page": p_num,
                    "content": results_map[p_num]
                })
                
            yield final_results
        except Exception as e:
            # Catch any errors during PDF processing
            raise Exception(f"PDF parsing failed: {str(e)}") from e
