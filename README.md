# S2L

Cell segmentation and ROI analysis tool. Supports Cellpose and StarDist segmentation engines with a modern PyQt6 interface.

## Features

- **Segmentation** — Run Cellpose (including SAM) or StarDist on microscopy images
- **ROI Analysis** — Convert segmentation masks to quantitative measurements (area, integrated density, mean gray value, standard deviation) exported as Excel spreadsheets
- **Dataset Viewer** — Browse large image folders with lazy-loaded thumbnails, zoom/pan preview, and keyboard navigation
- **Spreadsheet Import** — Parse experiment xlsx files (FIM sheet format) to extract image paths with well/channel/stage filters
- **Training** — Fine-tune Cellpose models on your own labelled data
- **Image Preprocessing** — Denoise, deblur, and upsample images using Cellpose restoration models

## Quick Install

### Prerequisites

- [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or Anaconda
- [Git](https://git-scm.com/)

### Windows

Download `install_and_run.bat` and double-click it. Or from a terminal:

```
curl -O https://raw.githubusercontent.com/we-02/S2L/main/install_and_run.bat
install_and_run.bat
```

The script will:
1. Clone the repository to `%USERPROFILE%\S2L`
2. Create a conda environment with Python 3.11
3. Install all dependencies
4. Detect your GPU and ask if you want CUDA acceleration
5. Launch the app

Subsequent runs pull updates, sync dependencies, and launch.

### macOS

```bash
curl -O https://raw.githubusercontent.com/we-02/S2L/main/install_and_run.sh
chmod +x install_and_run.sh
./install_and_run.sh
```

PyTorch is installed CPU-only on macOS (no CUDA support).

### Linux

```bash
curl -O https://raw.githubusercontent.com/we-02/S2L/main/install_and_run.sh
chmod +x install_and_run.sh
./install_and_run.sh
```

If an NVIDIA GPU is detected, the script asks whether to install PyTorch with CUDA support.

## Manual Install

If you prefer to set things up yourself:

```bash
git clone https://github.com/we-02/S2L.git
cd S2L
conda create -n S2L python=3.11 -y
conda activate S2L
pip install -r requirements.txt
```


For GPU acceleration on Windows/Linux:

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

For CPU-only (macOS or no NVIDIA GPU):

```bash
pip install torch torchvision
```

Then run:

```bash
python main.py
```

## Usage

### Folder Mode

1. Open the **Segmentation** page
2. Set input mode to **Folder**
3. Browse for your image directory and output directory
4. Choose an engine (Cellpose or StarDist) and model
5. Enable "Run segmentation" and/or "Run label → ROI analysis"
6. Click **Start processing**

### Spreadsheet Mode

1. Set input mode to **Spreadsheet**
2. Browse for your experiment `.xlsx` file
3. Click **Parse spreadsheet**
4. Use the Well / Stage / Channel / Type checkboxes to filter images
5. Set an output directory
6. Click **Start processing**

Masks are saved to the output directory. The ROI step generates Excel files and overlay images there as well.

### Dataset Viewer

Navigate to the **Viewer** page to browse image folders. Click **Open folder** or use the **View** buttons next to directory inputs on other pages. Supports:

- Thumbnail grid with lazy loading
- Click to preview, scroll to zoom, drag to pan
- Arrow keys to navigate, Escape to deselect
- Filename filter bar

## Project Structure

```
S2L/
├── main.py                      # Entry point
├── run_s2l.py                   # Alternative entry with dependency check
├── install_and_run.bat          # Windows launcher
├── install_and_run.sh           # macOS/Linux launcher
├── requirements.txt
├── s2l/
│   ├── core/
│   │   ├── segmenter.py         # Cellpose segmentation engine
│   │   ├── stardist_segmenter.py# StarDist segmentation engine
│   │   ├── roi_converter.py     # Mask → ROI measurements + overlay
│   │   ├── summary.py           # Summary Excel generation
│   │   ├── trainer.py           # Cellpose model training
│   │   └── spreadsheet_parser.py# Experiment xlsx parser
│   ├── ui/
│   │   ├── main_window.py       # Main app window + all pages
│   │   ├── theme.py             # Dark theme stylesheet
│   │   ├── dataset_viewer.py    # Image browser with thumbnails
│   │   └── preprocessing_gui.py # Image enhancement tool
│   └── utils/
│       └── sam_utils.py         # SAM model utilities
└── docs/                        # Sphinx documentation
```

## Requirements

- Python 3.11
- PyQt6
- NumPy < 2.1 (for numba/stardist compatibility)
- OpenCV, scikit-image, scipy
- pandas, openpyxl, xlsxwriter
- Cellpose >= 4.0
- PyTorch >= 2.0
- StarDist (optional)

## License

See [LICENSE](LICENSE) for details.
