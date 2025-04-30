# minimal_dia_test.py
import sys
import torch
import logging

# Basic logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

logging.info(f"--- Minimal Dia Test --- ")
logging.info(f"Python Version: {sys.version}")

# Check PyTorch and CUDA
try:
    logging.info(f"PyTorch version: {torch.__version__}")
    cuda_available = torch.cuda.is_available()
    logging.info(f"CUDA available via torch.cuda.is_available(): {cuda_available}")
    if cuda_available:
        logging.info(f"CUDA version detected by PyTorch: {torch.version.cuda}")
        logging.info(f"GPU Name: {torch.cuda.get_device_name(0)}")
    else:
        logging.warning("PyTorch cannot detect CUDA. Dia model loading will likely fail.")
except Exception as e:
    logging.error(f"Error checking PyTorch/CUDA: {e}")
    sys.exit(1)

# Attempt to import and load Dia
try:
    logging.info("Importing Dia library...")
    from dia.model import Dia
    logging.info("Dia library imported successfully.")
    
    model_id = "nari-labs/Dia-1.6B"
    compute_dtype = "float32" # Use float32 as it was more stable before
    
    logging.info(f"Attempting to load Dia model: {model_id} with dtype: {compute_dtype}...")
    # Load the model
    dia_model = Dia.from_pretrained(model_id, compute_dtype=compute_dtype)
    logging.info("--- Dia Model Loaded Successfully! ---")
    # Simple generation test (optional, loading is the main goal)
    # try:
    #     logging.info("Performing minimal generation test...")
    #     script = "[S1] Test successful."
    #     output = dia_model.generate(script, use_torch_compile=False)
    #     logging.info(f"Minimal generation successful. Output type: {type(output)}")
    # except Exception as gen_e:
    #     logging.error(f"Error during minimal generation test: {gen_e}")
        
except ImportError as ie:
    logging.error(f"Failed to import Dia library: {ie}. Ensure 'pip install git+https://github.com/nari-labs/dia.git' was successful.")
    sys.exit(1)
except Exception as e:
    logging.error(f"ERROR during Dia model loading: {e}", exc_info=True)
    logging.error("This likely indicates an incompatibility with the environment (PyTorch, CUDA, Drivers) or the library itself.")
    sys.exit(1)

logging.info("--- Minimal Test Script Finished ---") 