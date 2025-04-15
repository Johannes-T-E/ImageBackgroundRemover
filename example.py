import tkinter as tk
from tkinter import filedialog, Scale, ttk
from PIL import Image, ImageTk, ImageGrab
import pyautogui
import subprocess
import os
import win32clipboard
import threading
import re

class ColorPickerApp:
    def __init__(self, root):
        self.root = root
        self.root.geometry('2600x650')
        self.root.title('Canvas')

        # Initialize variables
        self.pixel_colors = []
        self.selected_image_path = ""
        self.original_image = None
        self.processed_image = None
        self.temp_folder = 'temp'
        self.tolerance = 0  # Tolerance value
        self.input_folder_path = ""
        self.output_folder_path = ""
        self.image_list = []
        self.fps = 10  # Default frames per second

        # Setup UI
        self.setup_ui()
        self.setup_temp_folder()

        # Bind key press event
        self.root.bind("<KeyPress-w>", self.save_pixel_color)
        self.root.bind("<Control-c>", self.copy_file_to_clipboard)
        self.root.bind("<Control-v>", self.paste_image)

    def setup_temp_folder(self):
        """Ensure the temporary folder exists."""
        if not os.path.exists(self.temp_folder):
            os.makedirs(self.temp_folder)

    def setup_ui(self):
        # Setup main home area directly without tabs
        self.setup_home_area()

    def setup_home_area(self):
        # Main frame for "Home" area
        self.home_frame = tk.Frame(self.root)
        self.home_frame.pack(fill='both', expand=True, padx=10, pady=10)

        self.setup_color_frame()
        self.setup_canvas_frame()
        self.setup_folder_options_frame()

    def setup_color_frame(self):
        # Frame for pixel color selection
        self.color_frame = tk.Frame(self.home_frame)
        self.color_frame.pack(side="left", fill='y')
        self.instruction_label = tk.Label(self.color_frame, text="Press 'W' to select a color", anchor="w", justify="left")
        self.instruction_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=5)

        self.label = tk.Label(self.color_frame, text="Pixel Color: ")
        self.label.grid(row=1, column=0, columnspan=2, sticky="w", padx=10, pady=5)

        self.color_list = tk.Frame(self.color_frame)
        self.color_list.grid(row=2, column=0, columnspan=2, sticky="w", padx=10, pady=5)

        # Slider for selecting tolerance
        self.tolerance_slider = Scale(self.color_frame, from_=0, to=50, orient="horizontal", label="Tolerance")
        self.tolerance_slider.grid(row=3, column=0, columnspan=2, sticky="we", padx=10, pady=10)

        self.auto_update = tk.BooleanVar(value=True)  # Auto-update toggle
        auto_update_checkbox = tk.Checkbutton(self.color_frame, text="Auto Update Image", variable=self.auto_update)
        auto_update_checkbox.grid(row=4, column=0, columnspan=2, sticky="w", padx=10, pady=5)

    def setup_canvas_frame(self):
        # Frame for the canvas
        self.canvas_frame = tk.Frame(self.home_frame)
        self.canvas_frame.pack(side="left", fill='both', expand=True, padx=10, pady=10)

        # Canvas for displaying original image
        self.canvas = tk.Canvas(self.canvas_frame, width=600, height=600, bg="white")
        self.canvas.pack(side="left", padx=10, pady=10)

        # Canvas for displaying processed (transparent) image
        self.transparent_canvas = tk.Canvas(self.canvas_frame, width=600, height=600, bg="white")
        self.transparent_canvas.pack(side="left", padx=10, pady=10)

    def setup_folder_options_frame(self):
        # Frame for folder and file options
        self.folder_frame = tk.Frame(self.home_frame)
        self.folder_frame.pack(side="right", fill='y')

        # Entry to display selected input folder
        self.input_folder_entry = tk.Entry(self.folder_frame, width=40)
        self.input_folder_entry.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        # Button to select input folder
        self.select_input_folder_button = tk.Button(self.folder_frame, text="Select Input Folder", command=self.select_input_folder)
        self.select_input_folder_button.grid(row=0, column=1, padx=10, pady=5, sticky="w")

        # Button to select a single image file
        self.select_image_button = tk.Button(self.folder_frame, text="Select Image", command=self.select_image_file)
        self.select_image_button.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        # Entry to display selected output folder
        self.output_folder_entry = tk.Entry(self.folder_frame, width=40)
        self.output_folder_entry.grid(row=2, column=0, padx=10, pady=5, sticky="w")

        # Button to select output folder
        self.select_output_folder_button = tk.Button(self.folder_frame, text="Select Output Folder", command=self.select_output_folder)
        self.select_output_folder_button.grid(row=2, column=1, padx=10, pady=5, sticky="w")

        # Button to update processed image
        self.update_image_button = tk.Button(self.folder_frame, text="Update Processed Image", command=self.display_processed_image)
        self.update_image_button.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        # Button to save processed image
        self.save_image_button = tk.Button(self.folder_frame, text="Save Processed Image", command=self.save_processed_image)
        self.save_image_button.grid(row=4, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        # Button to copy processed image to clipboard
        self.copy_to_clipboard_button = tk.Button(self.folder_frame, text="Copy to Clipboard", command=self.copy_file_to_clipboard)
        self.copy_to_clipboard_button.grid(row=5, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        # Entry for frames per second (FPS)
        self.fps_entry = tk.Entry(self.folder_frame, width=10)
        self.fps_entry.insert(0, "10")  # Default value
        self.fps_entry.grid(row=6, column=0, padx=10, pady=5, sticky="w")

        self.fps_label = tk.Label(self.folder_frame, text="FPS:")
        self.fps_label.grid(row=6, column=1, padx=10, pady=5, sticky="w")

        # Button to create GIF
        self.create_gif_button = tk.Button(self.folder_frame, text="Create GIF", command=self.start_gif_creation)
        self.create_gif_button.grid(row=7, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        # Progress bar for GIF creation
        self.progress_bar = ttk.Progressbar(self.folder_frame, orient="horizontal", length=300, mode="determinate")
        self.progress_bar.grid(row=8, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        # Label for displaying time elapsed
        self.time_label = tk.Label(self.folder_frame, text="Time Elapsed: 0s")
        self.time_label.grid(row=9, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        # Label for displaying current processing status
        self.status_label = tk.Label(self.folder_frame, text="Status: Waiting")
        self.status_label.grid(row=10, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        # Label for displaying current image number
        self.image_number_label = tk.Label(self.folder_frame, text="Image: 0/0")
        self.image_number_label.grid(row=11, column=0, columnspan=2, padx=10, pady=5, sticky="w")

    def copy_file_to_clipboard(self, event=None):
        if self.processed_image:
            temp_image_path = os.path.join(self.temp_folder, 'processed_image.png')
            self.processed_image.save(temp_image_path)  # Save image to the temporary folder
            self.processed_image_path = temp_image_path  # Update the path stored

            # Properly format the path to avoid issues in the command line
            formatted_path = self.processed_image_path.replace('\\', '\\\\')

            # Prepare the PowerShell command
            command = f"powershell -command \"Set-Clipboard -LiteralPath '{formatted_path}'\""
            
            # Execute the command
            subprocess.run(command, shell=True)
            print("File path copied to clipboard:", self.processed_image_path)

    def paste_image(self, event=None):
        try:
            # Try to grab an image directly from the clipboard
            clipboard_image = ImageGrab.grabclipboard()
            if isinstance(clipboard_image, Image.Image):
                # If it's an image, process it
                self.original_image = clipboard_image
                self.display_original_image()
                self.display_processed_image()
                print("Image pasted directly from clipboard.")
            else:
                # If no image, check for file paths
                win32clipboard.OpenClipboard()
                if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_HDROP):
                    file_paths = win32clipboard.GetClipboardData(win32clipboard.CF_HDROP)
                    win32clipboard.CloseClipboard()
                    if file_paths:
                        # Assuming the first file in the list is what we want
                        image_path = file_paths[0]
                        self.original_image = Image.open(image_path)
                        self.display_original_image()
                        self.display_processed_image()
                        print("Image loaded from file path in clipboard.")
                    else:
                        print("Clipboard contains file paths but none were accessible.")
                else:
                    win32clipboard.CloseClipboard()
                    print("No image or file path found in clipboard.")
        except Exception as e:
            print("Error pasting image:", e)

    def get_clipboard_data(self, format):
        try:
            # Prepare the PowerShell command to get clipboard data of specified format
            command = "powershell -command \"$data = Get-Clipboard -Format {}; if ($data) {{ $data }}\"".format(format)

            # Execute the command and retrieve data
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()

        except Exception as e:
            print("Error getting clipboard {}:".format(format), e)
        return None

    def get_pixel_color(self):
        x, y = pyautogui.position()
        img = ImageGrab.grab().load()
        try:
            color = img[x, y]
        except IndexError:
            color = (255, 255, 255)  # Default color if index is out of range
        self.label.config(text=f"Pixel Color: {color}")
        self.label.after(100, self.get_pixel_color)  # Update every 100 milliseconds

    def save_pixel_color(self, event):
        if event.keysym == 'w':
            x, y = pyautogui.position()
            img = ImageGrab.grab().load()
            try:
                color = img[x, y]
                self.pixel_colors.append(color)
                self.update_color_list()
            except IndexError:
                pass  # Ignore if index is out of range

    def update_color_list(self):
        # Clear previous entries
        for widget in self.color_list.winfo_children():
            widget.destroy()
            
        # Display new entries
        for i, color in enumerate(self.pixel_colors):
            color_label = tk.Label(self.color_list, text=f"{i+1}: {color}", anchor="w", justify="left")
            color_label.grid(row=i, column=0, sticky="w")
            
            hex_color = self.rgb_to_hex(color)
            canvas = tk.Canvas(self.color_list, width=20, height=20, bg=hex_color, highlightthickness=0)
            canvas.grid(row=i, column=1, padx=(0, 10), pady=2, sticky="w")
            
            delete_button = tk.Button(self.color_list, text="Delete", command=lambda i=i: self.delete_color(i))
            delete_button.grid(row=i, column=2, padx=(0, 10), pady=2, sticky="w")

        # Update the processed image if auto-update is enabled
        if self.auto_update:  # Assuming there's a toggle setting called self.auto_update
            self.display_processed_image()

    def rgb_to_hex(self, rgb): 
        return '#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2])

    def delete_color(self, index):
        del self.pixel_colors[index]
        self.update_color_list()

    def select_input_folder(self):
        self.input_folder_path = filedialog.askdirectory()
        self.input_folder_entry.delete(0, tk.END)
        self.input_folder_entry.insert(0, self.input_folder_path)
        self.load_images_from_folder()

    def load_images_from_folder(self):
        if self.input_folder_path:
            self.image_list = sorted([os.path.join(self.input_folder_path, f) for f in os.listdir(self.input_folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))], key=self.natural_sort_key)
            if self.image_list:
                self.original_image = Image.open(self.image_list[0])
                self.display_original_image()

    def natural_sort_key(self, s):
        _nsre = re.compile('([0-9]+)')
        return [int(text) if text.isdigit() else text.lower() for text in re.split(_nsre, s)]

    def select_output_folder(self):
        self.output_folder_path = filedialog.askdirectory()
        self.output_folder_entry.delete(0, tk.END)
        self.output_folder_entry.insert(0, self.output_folder_path)

    def select_image_file(self):
        self.selected_image_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png;*.jpg;*.jpeg")])
        if self.selected_image_path:
            self.original_image = Image.open(self.selected_image_path)
            self.display_original_image()

    def display_original_image(self):
        if self.original_image:
            # Calculate aspect ratio and set canvas dimensions
            aspect_ratio = self.original_image.width / self.original_image.height
            max_canvas_size = 1000  # Define a maximum size to maintain UI consistency
            if aspect_ratio > 1:
                # Image is wider than tall
                canvas_width = max_canvas_size
                canvas_height = int(max_canvas_size / aspect_ratio)
            else:
                # Image is taller than wide or square
                canvas_height = max_canvas_size
                canvas_width = int(max_canvas_size * aspect_ratio)

            # Configure original canvas size
            self.canvas.config(width=canvas_width, height=canvas_height)
            
            # Resize and display image on the original canvas
            img = self.resize_image(self.original_image, (canvas_width, canvas_height))
            photo = ImageTk.PhotoImage(img)
            self.canvas.delete("all")
            self.canvas.image = photo  # Keep reference
            self.canvas.create_image(0, 0, anchor="nw", image=photo)

            # Apply the same dimensions to the processed image canvas
            self.transparent_canvas.config(width=canvas_width, height=canvas_height)

    def display_processed_image(self):
        print("Entering display_processed_image function")
        # Ensure processed_image is updated here similar to the old version
        if self.original_image:
            self.processed_image = self.make_transparent(self.original_image)
            # Refresh canvas info and get current size
            self.transparent_canvas.update_idletasks()
            canvas_width = self.transparent_canvas.winfo_width()
            canvas_height = self.transparent_canvas.winfo_height()

            print("Canvas dimensions:", canvas_width, canvas_height)  # Debug output

            img = self.resize_image(self.processed_image, (canvas_width, canvas_height))
            photo = ImageTk.PhotoImage(img)
            self.transparent_canvas.delete("all")
            self.transparent_canvas.image = photo  # Maintain reference
            self.transparent_canvas.create_image((canvas_width - img.width) // 2, (canvas_height - img.height) // 2, anchor="nw", image=photo)

    def resize_image(self, img, max_size=(1000, 1000)):
        original_width, original_height = img.size
        ratio = min(max_size[0] / original_width, max_size[1] / original_height)
        new_width = int(original_width * ratio)
        new_height = int(original_height * ratio)
        return img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def make_transparent(self, img):
        """ Update to use tolerance for transparency """
        tolerance = self.tolerance_slider.get()
        img = img.convert("RGBA")
        datas = img.getdata()
        new_data = []

        for item in datas:
            match = False
            for color in self.pixel_colors:
                if all(abs(item[i] - color[i]) <= tolerance for i in range(3)):
                    new_data.append((255, 255, 255, 0))  # Make transparent
                    match = True
                    break
            if not match:
                new_data.append(item)

        img.putdata(new_data)
        return img

    def save_processed_image(self):
        if self.processed_image:
            save_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png")])
            if save_path:
                self.processed_image.save(save_path)

    def start_gif_creation(self):
        gif_thread = threading.Thread(target=self.create_gif)
        gif_thread.start()

    def create_gif(self):
        if not self.image_list or not self.output_folder_path:
            print("Input folder or output folder not selected.")
            return

        fps = int(self.fps_entry.get())
        duration = 1000 // fps  # Duration of each frame in milliseconds

        processed_images = []
        self.progress_bar["value"] = 0
        self.progress_bar["maximum"] = len(self.image_list)
        for i, image_path in enumerate(self.image_list):
            image = Image.open(image_path)
            transparent_image = self.make_transparent(image)
            processed_images.append(transparent_image)
            self.progress_bar["value"] += 1
            self.root.update_idletasks()  # Update the progress bar

        gif_path = os.path.join(self.output_folder_path, 'output.gif')
        processed_images[0].save(gif_path, save_all=True, append_images=processed_images[1:], duration=duration, loop=0, transparency=0, disposal=2)

        print(f"GIF created at: {gif_path}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ColorPickerApp(root)
    root.mainloop()  # Run the Tkinter event loop
