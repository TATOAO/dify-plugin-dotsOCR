import base64
import json
from io import BytesIO
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

class DotsOCRClient:
    def __init__(self, ip='172.20.201.93', port=8001, protocol='http', model_name='model', timeout=300):
        """
        Initialize dots.ocr client
        :param ip: vLLM server IP
        :param port: vLLM server port
        :param protocol: http or https
        :param model_name: model name (default model)
        :param timeout: request timeout in seconds
        """
        self.addr = f"{protocol}://{ip}:{port}/v1"
        self.model_name = model_name
        self.timeout = timeout
        if HAS_OPENAI:
            self.client = OpenAI(api_key="0", base_url=self.addr)
        
    def image_to_base64(self, image):
        """Convert PIL Image to base64 string"""
        buffered = BytesIO()
        if image.mode != 'RGB':
            image = image.convert('RGB')
        image.save(buffered, format="JPEG")
        return f"data:image/jpeg;base64,{base64.b64encode(buffered.getvalue()).decode('utf-8')}"

    def _get_prompt(self, mode):
        """
        Get dots.ocr specific Prompt
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
        prompt = self._get_prompt(prompt_mode)
        base64_image = self.image_to_base64(image)
        
        # vLLM needs specific prompt prefix to recognize image
        full_prompt = f"<|img|><|imgpad|><|endofimg|>{prompt}"
        
        if HAS_OPENAI:
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
                timeout=self.timeout
            )
            return response.choices[0].message.content
        else:
            # Fallback to requests
            payload = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": base64_image}},
                            {"type": "text", "text": full_prompt},
                        ],
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 16384
            }
            res = requests.post(f"{self.addr}/chat/completions", json=payload, timeout=self.timeout)
            res.raise_for_status()
            return res.json()['choices'][0]['message']['content']

    def parse_pdf(self, pdf_bytes, prompt_mode="prompt_layout_all_en", max_concurrency=20):
        """
        Parse PDF file (parallel calling dots.ocr)
        :param pdf_bytes: PDF file content in bytes
        """
        if not HAS_FITZ:
            raise ImportError("Please install pymupdf (pip install pymupdf) to process PDF files.")
        
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        except Exception as e:
            raise ValueError(f"Failed to open PDF: {str(e)}")
            
        if len(doc) == 0:
            return []
            
        pages_to_process = []
        
        for page_num in range(len(doc)):
            try:
                page = doc[page_num]
                pix = page.get_pixmap(dpi=200)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                pages_to_process.append((page_num + 1, img))
            except Exception as e:
                # If a specific page fails to render, we'll mark it as an error in the result
                pages_to_process.append((page_num + 1, None))
        
        results_map = {}
        
        def process_page(page_info):
            page_num, img = page_info
            if img is None:
                return page_num, "Error: Failed to render page"
            output = self.inference(img, prompt_mode)
            return page_num, output

        with ThreadPoolExecutor(max_workers=max_concurrency) as executor:
            future_to_page = {executor.submit(process_page, page): page[0] for page in pages_to_process}
            for future in as_completed(future_to_page):
                page_num = future_to_page[future]
                try:
                    p_num, content = future.result()
                    results_map[p_num] = content
                except Exception as exc:
                    results_map[page_num] = f"Error: {str(exc)}"

        # Sort results by page number
        final_results = []
        for p_num in sorted(results_map.keys()):
            final_results.append({
                "page": p_num,
                "content": results_map[p_num]
            })
            
        return final_results
