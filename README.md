# S2L - Cellpose SAM Edition (Merged)

**Segmentation to Labels with Cellpose-SAM Integration**

A comprehensive GUI application for cellular image segmentation, ROI analysis, model training, and image preprocessing. Features the latest Cellpose-SAM technology for superhuman generalization, plus traditional Cellpose models and custom model support.

## 🚀 New Features

### Modern Interface Design
- **Sleek Dark Theme**: Professional dark theme with purple accents
- **Multi-Tab Interface**: Segmentation, Training, and Helpers tabs
- **Intuitive Icons**: Emoji-based visual cues throughout the interface
- **Responsive Design**: Optimized for various screen sizes
- **Smooth Animations**: Hover effects and visual feedback

### Cellpose-SAM Integration
- **Superhuman Generalization**: State-of-the-art segmentation across diverse cell types
- **Diameter Invariant**: No need to specify cell diameter (though you still can)
- **Enhanced Accuracy**: Improved performance on challenging images
- **Automatic Model Management**: SAM model downloads automatically on first use

### Model Support
- **12+ Built-in Models**: SAM, cytoplasm, nuclei, tissue, bacteria, yeast models
- **Custom Model Support**: Load and use your own trained models
- **Model Training**: Built-in training interface for creating custom models
- **Automatic Fallbacks**: Graceful handling when preferred models aren't available

### Advanced Features
- **Image Preprocessing**: Denoise, deblur, and enhance images before segmentation
- **Batch Processing**: Process multiple images automatically
- **Progress Tracking**: Real-time progress bars for all operations
- **External Tool Integration**: Launch Cellpose GUI, Himena viewer, and more

### Enhanced Performance
- **Optimized File Handling**: Faster processing with pathlib and caching
- **GPU Acceleration**: Better CUDA integration for faster processing
- **Memory Optimization**: Reduced memory usage through vectorization
- **Error Recovery**: Robust error handling and fallback options

## 📋 Requirements

### System Requirements
- Python 3.8+
- 8GB+ RAM (16GB+ recommended for large images)
- CUDA-compatible GPU (optional but recommended)

### Dependencies
- **Cellpose ≥4.0.0** (for SAM support)
- **PyTorch ≥2.0.0** (for SAM model)
- **PyQt6** (GUI framework)
- **OpenCV, NumPy, Pandas** (image processing)

## 🛠️ Installation

### Quick Install
```bash
# Clone the repository
git clone <repository-url>
cd S2L

# Install dependencies
pip install -r requirements.txt

# Test SAM compatibility
python test_sam.py

# Run the application
python main.py
```

### Detailed Setup
See [SAM_SETUP.md](SAM_SETUP.md) for comprehensive installation instructions.

## 🎯 Usage

### Basic Workflow

#### Segmentation Tab
1. **Launch Application**: `python main.py`
2. **Select Directories**: Choose base directory (images) and output directory
3. **Choose Model**: Enable "Use Cellpose-SAM" (recommended) or select from 12+ models
4. **Custom Models**: Optionally specify path to custom trained model
5. **Configure Settings**: Set diameter (optional for SAM) and processing options
6. **Run Processing**: Click "Run Process" and monitor progress
7. **Review Results**: Check output directory for masks, ROIs, and summary data

#### Training Tab
1. **Select Training Data**: Choose directory with images and masks
2. **Configure Training**: Set model type, channels, epochs, learning rate
3. **Set Filters**: Specify image and mask file filters
4. **Train Model**: Click "Train" and wait for completion
5. **Use Model**: Load trained model in Segmentation tab

#### Helpers Tab
- **Cellpose GUI**: Launch official Cellpose interface
- **Preprocessing**: Open image enhancement tool
- **Himena**: Launch advanced image viewer
- **Verify Installation**: Check system compatibility
- **Test SAM**: Verify SAM functionality

### Processing Options
- **Run Segmentation**: Generate cell masks using Cellpose/SAM
- **Run Label to ROI**: Convert masks to ROI measurements and visualizations
- **Model Selection**: Choose from SAM or traditional Cellpose models
- **Diameter Setting**: Optional for SAM, required for traditional models

### Output Files
- **Masks**: `*_cp_masks.png` - Segmentation masks
- **ROI Data**: `*.xlsx` - Quantitative measurements per cell
- **Visualizations**: `*_ROI.png` - Overlay images with ROI labels
- **Summary**: `SummarySheet/Summary.xlsx` - Aggregated results

## 🔧 Features

### Segmentation Models
| Model | Description | Diameter Required | Best For |
|-------|-------------|-------------------|----------|
| **cpsam** | Cellpose-SAM (Latest) | No | General use, diverse cell types |
| cyto3 | Cytoplasm v3 | Yes | Traditional cytoplasm segmentation |
| nuclei | Nuclear model | Yes | Nuclear segmentation |
| tissuenet_cp3 | TissueNet | Yes | Tissue-level analysis |

### Advanced Features
- **Batch Processing**: Process multiple images automatically
- **Progress Monitoring**: Real-time progress bars for each step
- **Error Recovery**: Automatic fallback and error reporting
- **Stop/Resume**: Cancel processing mid-way if needed
- **CUDA Detection**: Automatic GPU acceleration when available

## 📊 Performance Tips

### For Best Results
- **Image Quality**: Use well-contrasted images with clear cell boundaries
- **File Formats**: Supports .tif, .tiff, .png, .jpg, .jpeg formats
- **Image Size**: Resize very large images for faster processing
- **GPU Usage**: Enable CUDA for 5-10x speed improvement

### SAM-Specific Tips
- No diameter specification needed (model adapts automatically)
- Works well across different cell types without retraining
- More robust to imaging artifacts and noise
- Optimal for diverse datasets

## 🐛 Troubleshooting

### Common Issues

**"SAM Status: Cellpose version X.X.X is too old"**
```bash
pip install --upgrade "cellpose[gui]>=4.0.0"
```

**"SAM Status: PyTorch is not installed"**
```bash
pip install torch>=2.0.0 torchvision>=0.15.0
```

**Out of memory errors**
- Reduce image size or process individually
- Use CPU mode if GPU memory insufficient
- Close other applications to free memory

**Model download fails**
- Ensure stable internet connection
- Check firewall settings
- Model caches locally after first download

### Performance Issues
- **Slow processing**: Enable CUDA, reduce image size, or process in batches
- **High memory usage**: Process images individually or reduce batch size
- **GUI freezing**: Check terminal for error messages, restart if needed

## 📁 File Structure
```
S2L/
├── main.py              # Main GUI application
├── segment.py           # Segmentation engine
├── l2r.py              # Labels to ROI conversion
├── mastersheet.py      # Summary sheet generation
├── sam_utils.py        # SAM-specific utilities
├── test_sam.py         # SAM compatibility test
├── requirements.txt    # Python dependencies
├── SAM_SETUP.md       # Detailed setup guide
└── README.md          # This file
```

## 🔬 Scientific Usage

### Citation
If you use this software in your research, please cite:
- **Cellpose-SAM**: [bioRxiv preprint](https://www.biorxiv.org/content/10.1101/2025.04.28.651001v1)
- **Original Cellpose**: Stringer, C., Wang, T., Michaelos, M. et al. Nature Methods (2021)

### Data Output
- **Quantitative Metrics**: Area, integrated density, mean gray value, standard deviation
- **Statistical Analysis**: Per-cell measurements in Excel format
- **Visualization**: Labeled overlay images for publication
- **Batch Analysis**: Summary statistics across multiple images

## 🤝 Contributing

### Development Setup
```bash
git clone <repository-url>
cd S2L
pip install -r requirements.txt
python test_sam.py  # Verify setup
```

### Reporting Issues
- Use GitHub Issues for bug reports
- Include system information and error messages
- Provide sample images if possible (anonymized)

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Cellpose Team**: For the amazing segmentation models
- **SAM Authors**: For the foundational SAM architecture
- **Community**: For feedback and contributions

## 📞 Support

- **Documentation**: Check SAM_SETUP.md for detailed instructions
- **Issues**: Open GitHub issues for bugs and feature requests
- **Cellpose Support**: Visit [Cellpose GitHub](https://github.com/MouseLand/cellpose)

---

**Version**: 2.0.0 (SAM Edition)  
**Last Updated**: 2024  
**Compatibility**: Cellpose ≥4.0.0, Python 3.8+