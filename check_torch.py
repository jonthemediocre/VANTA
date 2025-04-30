# check_torch.py
import torch
import sys
import os

print(f"--- Environment Info ---")
print(f"Python Executable: {sys.executable}")
print(f"Python Version: {sys.version}")
# Check if running in the expected environment
expected_env_path = os.path.join("Users", "Jonbr", "AppData", "Local", "NVIDIA", "ChatWithRTX", "env_nvd_rag")
if expected_env_path.lower() not in sys.executable.lower():
    print(f"\nWARNING: Running Python from an unexpected path. Make sure the correct environment is activated.")
    print(f"Expected environment path should contain: {expected_env_path}\n")


print(f"\n--- PyTorch Info ---")
try:
    print(f"PyTorch version: {torch.__version__}")
    cuda_available = torch.cuda.is_available()
    print(f"CUDA available via torch.cuda.is_available(): {cuda_available}")

    if cuda_available:
        print(f"CUDA version detected by PyTorch: {torch.version.cuda}")
        print(f"cuDNN version detected by PyTorch: {torch.backends.cudnn.version()}")
        print(f"Number of GPUs detected: {torch.cuda.device_count()}")
        try:
            print(f"Active GPU Name: {torch.cuda.get_device_name(0)}")
            print(f"Active GPU Compute Capability: {torch.cuda.get_device_capability(0)}")
            # Simple test computation
            print("\nPerforming a simple CUDA tensor operation...")
            a = torch.tensor([1.0, 2.0]).cuda()
            b = torch.tensor([3.0, 4.0]).cuda()
            c = a + b
            print(f"Test computation result (should be on CUDA device): {c}")
            print("CUDA tensor operation successful.")
        except Exception as e:
            print(f"\nERROR during GPU detail retrieval or test computation: {e}")
            print("This might indicate an issue with the CUDA setup or driver compatibility despite CUDA being reported as available.")
    else:
        print("\nPyTorch cannot detect a CUDA-enabled GPU.")
        print("Ensure CUDA drivers are installed correctly and that your PyTorch build supports your CUDA version.")

except Exception as e:
    print(f"\nERROR importing or interacting with PyTorch: {e}")
    print("Please ensure PyTorch is installed correctly in this environment.")

print("\n--- Check Complete ---") 