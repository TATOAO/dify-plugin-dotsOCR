from dify_plugin_dotsocr.plugin import DotsOCRPlugin
import os

def main():
    # This is a sample usage of the DotsOCRPlugin locally
    # In a real Dify environment, Dify calls the run method with appropriate inputs and settings
    
    plugin = DotsOCRPlugin()
    
    # Mock settings
    settings = {
        "server_ip": "172.20.201.93",
        "server_port": 8001,
        "protocol": "http",
        "model_name": "model",
        "timeout": 300
    }
    
    # Mock inputs for an image (if you have one)
    # For demonstration, we'll just print the structure
    print("Dify Plugin DotsOCR initialized.")
    print(f"Server: {settings['protocol']}://{settings['server_ip']}:{settings['server_port']}")
    
    # Example of how inputs would look
    inputs = {
        "file": {
            "extension": "pdf",
            "content": b"..." # This would be the actual file bytes
        },
        "prompt_mode": "prompt_layout_all_en",
        "max_concurrency": 10
    }
    
    print("\nSample Inputs structure:")
    print(inputs)
    
    print("\nTo run the plugin, Dify would execute:")
    print("result = plugin.run(inputs, settings)")

if __name__ == "__main__":
    main()
