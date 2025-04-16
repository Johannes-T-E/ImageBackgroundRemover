import sys
import json
import numpy as np
import cv2
from PIL import Image
from dataclasses import dataclass
from typing import List, Tuple
import os

@dataclass
class Color:
    rgb: Tuple[int, int, int]
    tolerance: int = 0

class ImageProcessor:
    def __init__(self):
        self.colors: List[Color] = []
        self.current_image = None
        self.processed_image = None
        self.tolerances: List[int] = []
        self.edge_detection: bool = False
        self.edge_sensitivity: int = 50

    def process_message(self, message):
        try:
            data = json.loads(message)
            command = data.get('command')
            
            if command == 'add-color':
                color = tuple(data['color'])
                tolerance = data.get('tolerance', 0)
                self.add_color(color, tolerance)
                
            elif command == 'update-tolerance':
                index = data.get('index')
                tolerance = data['tolerance']
                self.update_tolerance(tolerance, index)
                
            elif command == 'process-image':
                image_path = data['path']
                # Clear existing colors and add new ones from the message
                self.colors.clear()
                for color_data in data.get('colors', []):
                    self.add_color(tuple(color_data['rgb']), color_data['tolerance'])
                self.load_and_process_image(image_path)
                
            elif command == 'clear-colors':
                self.clear_colors()
                
            elif command == 'update-edge-settings':
                enabled = data.get('enabled')
                sensitivity = data.get('sensitivity')
                self.update_edge_settings(enabled, sensitivity)
                    
            self.send_response({'status': 'success'})
            
        except Exception as e:
            self.send_response({'status': 'error', 'message': str(e)})

    def add_color(self, color: Tuple[int, int, int], tolerance: int):
        self.colors.append(Color(rgb=color, tolerance=tolerance))
        if self.current_image:
            self.process_image()

    def update_tolerance(self, tolerance: int, index: int = None):
        if index is not None:
            if 0 <= index < len(self.colors):
                self.colors[index].tolerance = tolerance
        else:
            for color in self.colors:
                color.tolerance = tolerance
                
        if self.current_image:
            self.process_image()

    def clear_colors(self):
        self.colors.clear()
        self.tolerances.clear()
        if self.current_image:
            self.process_image()

    def load_and_process_image(self, image_path: str):
        try:
            # Open and convert image to RGBA mode
            img = Image.open(image_path)
            self.current_image = img.convert('RGBA')
            self.process_image()
        except Exception as e:
            self.send_response({'status': 'error', 'message': f'Failed to load image: {str(e)}'})

    def process_image(self):
        if not self.current_image or not self.colors:
            # Send empty result when no colors are selected
            self.processed_image = self.current_image
            self.save_and_notify()
            return
            
        # Convert to numpy array for processing
        img_array = np.array(self.current_image)
        
        # Ensure image is in RGBA format (should already be, but let's be safe)
        if len(img_array.shape) == 2:  # Grayscale
            img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGBA)
        elif img_array.shape[-1] == 3:  # RGB
            img_array = np.concatenate([img_array, np.full((*img_array.shape[:2], 1), 255)], axis=-1)
        elif img_array.shape[-1] == 4:  # Already RGBA
            pass
        else:
            raise ValueError(f"Unexpected image format with shape {img_array.shape}")

        # Create mask
        mask = np.zeros(img_array.shape[:2], dtype=np.uint8)
        
        # Process each pixel using per-channel comparison
        for color in self.colors:
            if color.tolerance == 0:
                # For exact matches, use a very small tolerance to catch nearly-exact matches
                effective_tolerance = 2
                r_match = np.abs(img_array[:,:,0].astype(np.int16) - color.rgb[0]) <= effective_tolerance
                g_match = np.abs(img_array[:,:,1].astype(np.int16) - color.rgb[1]) <= effective_tolerance
                b_match = np.abs(img_array[:,:,2].astype(np.int16) - color.rgb[2]) <= effective_tolerance
                color_match = r_match & g_match & b_match
            else:
                # For tolerance > 0, use the specified tolerance
                r_match = np.abs(img_array[:,:,0].astype(np.int16) - color.rgb[0]) <= color.tolerance
                g_match = np.abs(img_array[:,:,1].astype(np.int16) - color.rgb[1]) <= color.tolerance
                b_match = np.abs(img_array[:,:,2].astype(np.int16) - color.rgb[2]) <= color.tolerance
                color_match = r_match & g_match & b_match

            mask = cv2.bitwise_or(mask, color_match.astype(np.uint8) * 255)
        
        # Apply mask
        result = img_array.copy()
        result[mask > 0] = [0, 0, 0, 0]
        
        # Convert back to PIL Image
        self.processed_image = Image.fromarray(result)
        self.save_and_notify()

    def save_and_notify(self):
        if self.processed_image:
            try:
                # Ensure temp directory exists
                os.makedirs('temp', exist_ok=True)
                
                # Save to temporary file with normalized absolute path
                temp_path = os.path.abspath(os.path.join('temp', 'processed_image.png'))
                temp_path = temp_path.replace('\\', '/')
                
                # Save with alpha channel
                self.processed_image.save(temp_path, 'PNG')
                
                # Notify frontend with normalized path
                self.send_response({
                    'status': 'success',
                    'type': 'image-processed',
                    'path': temp_path
                })
            except Exception as e:
                self.send_response({
                    'status': 'error',
                    'message': f'Failed to save processed image: {str(e)}'
                })

    def send_response(self, data):
        """Send a JSON response to the Node.js process through stdout."""
        try:
            json_str = json.dumps(data)
            print(json_str)
            sys.stdout.flush()
        except Exception as e:
            error_msg = json.dumps({
                'status': 'error',
                'message': f'Failed to send response: {str(e)}'
            })
            print(error_msg)
            sys.stdout.flush()

    def update_edge_settings(self, enabled: bool, sensitivity: int):
        self.edge_detection = enabled
        self.edge_sensitivity = sensitivity
        if self.current_image:
            self.process_image()

def main():
    processor = ImageProcessor()
    
    for line in sys.stdin:
        processor.process_message(line)

if __name__ == "__main__":
    main() 