"""Phase 1 verification: CUDA + PyTorch + Kornia."""
import sys

def main():
    print("=" * 50)
    print("PHASE 1 VERIFICATION")
    print("=" * 50)
    
    # Python
    print(f"\nPython version: {sys.version.split()[0]}")
    
    # PyTorch
    try:
        import torch
        print(f"\nPyTorch version: {torch.__version__}")
        print(f"CUDA available: {torch.cuda.is_available()}")
        
        if torch.cuda.is_available():
            print(f"CUDA version: {torch.version.cuda}")
            print(f"GPU count: {torch.cuda.device_count()}")
            print(f"GPU name: {torch.cuda.get_device_name(0)}")
            
            # Quick tensor test
            x = torch.randn(1000, 1000).cuda()
            y = x @ x
            print(f"GPU tensor test: PASSED (matrix multiply works)")
            
            # Memory info
            mem_total = torch.cuda.get_device_properties(0).total_memory / 1e9
            print(f"GPU memory: {mem_total:.1f} GB")
        else:
            print("ERROR: CUDA not available to PyTorch")
            return 1
            
    except ImportError as e:
        print(f"ERROR: PyTorch not installed: {e}")
        return 1
    
    # Kornia
    try:
        import kornia
        print(f"\nKornia version: {kornia.__version__}")
        
        # Quick Kornia GPU test
        img = torch.randn(1, 1, 64, 64).cuda()
        grad = kornia.filters.sobel(img)
        print(f"Kornia GPU test: PASSED (Sobel filter works)")
        
    except ImportError as e:
        print(f"ERROR: Kornia not installed: {e}")
        return 1
    
    # OpenCV
    try:
        import cv2
        print(f"\nOpenCV version: {cv2.__version__}")
    except ImportError:
        print("\nWARNING: OpenCV not installed")
    
    print("\n" + "=" * 50)
    print("PHASE 1 COMPLETE: GPU ENVIRONMENT READY")
    print("=" * 50)
    return 0

if __name__ == "__main__":
    sys.exit(main())
