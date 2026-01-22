import unittest
from unittest.mock import MagicMock, patch
from dify_plugin_dotsocr.client import DotsOCRClient
from PIL import Image
import io

class TestDotsOCRClient(unittest.TestCase):
    def setUp(self):
        self.client = DotsOCRClient(ip='127.0.0.1', port=8001)

    def test_image_to_base64(self):
        img = Image.new('RGB', (100, 100), color='red')
        base64_str = self.client.image_to_base64(img)
        self.assertTrue(base64_str.startswith('data:image/jpeg;base64,'))

    def test_get_prompt(self):
        prompt = self.client._get_prompt("prompt_ocr")
        self.assertEqual(prompt, "Extract the text content from this image.")
        
        prompt = self.client._get_prompt("invalid_mode")
        self.assertIn("Please output the layout information", prompt)

    @patch('requests.post')
    def test_inference_requests(self, mock_post):
        # Mocking requests response when HAS_OPENAI is False or forced to False
        with patch('dify_plugin_dotsocr.client.HAS_OPENAI', False):
            mock_response = MagicMock()
            mock_response.json.return_value = {
                'choices': [{'message': {'content': 'test result'}}]
            }
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            img = Image.new('RGB', (10, 10))
            result = self.client.inference(img)
            self.assertEqual(result, 'test result')

if __name__ == '__main__':
    unittest.main()
