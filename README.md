# Image Background Remover

A modern Electron application for removing backgrounds from images using color-based selection.

## Prerequisites

Before you begin, ensure you have the following installed:
- [Node.js](https://nodejs.org/) (v16 or higher)
- [Python](https://www.python.org/) (v3.8 or higher)
- [Git](https://git-scm.com/)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ImageBackgroundRemover.git
cd ImageBackgroundRemover
```

2. Set up Python virtual environment:
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

3. Install Node.js dependencies:
```bash
npm install
```

## Running the Application

1. Make sure your Python virtual environment is activated (see step 2 above)

2. Start the application:
```bash
# For development (with DevTools):
npm run dev

# For production:
npm start
```

## Features

- Load images from file or clipboard
- Color-based background removal
- Adjustable color tolerance
- Save processed images
- Copy processed images to clipboard
- Modern, intuitive user interface

## Development

To build the application for distribution:
```bash
npm run build
```

The built application will be available in the `dist` directory.

## Project Structure

- `src/` - Source code directory
  - `backend/` - Python backend service
  - `ui/` - Electron frontend
- `temp/` - Temporary files (created automatically)
- `assets/` - Application assets

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the ISC License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- OpenCV for image processing
- Electron for the desktop framework
- NumPy for numerical computations 