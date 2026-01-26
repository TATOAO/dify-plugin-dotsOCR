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
    def __init__(self, endpoint: str, model_name: str = 'model', api_key: str = '0'):
        """
        Initialize dots.ocr client
        :param endpoint: vLLM server endpoint (e.g. http://172.20.201.93:8001/v1)
        :param model_name: Model name (default 'model')
        :param api_key: API key (default '0')
        """
        self.endpoint = endpoint.rstrip('/')
        self.model_name = model_name
        self.client = OpenAI(api_key=api_key, base_url=self.endpoint)
        
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
        )
        return response.choices[0].message.content

    def parse_pdf(self, pdf_stream: bytes, prompt_mode="prompt_layout_all_en", max_concurrency=20):
        """
        Parse PDF file (parallel call to dots.ocr)
        """
        doc = fitz.open(stream=pdf_stream, filetype="pdf")
        pages_to_process = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=200)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            pages_to_process.append((page_num + 1, img))
        
        results_map = {}
        
        def process_page(page_info):
            page_num, img = page_info
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
                    results_map[page_num] = f"Error: {exc}"

        final_results = []
        for p_num in sorted(results_map.keys()):
            final_results.append({
                "page": p_num,
                "content": results_map[p_num]
            })
            
        return final_results
