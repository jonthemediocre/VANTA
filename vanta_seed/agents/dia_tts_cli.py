import argparse
import logging
import sys

try:
    from dia.model import Dia
except ImportError:
    logging.error("DiaTTS CLI: Failed to import 'dia' library. Ensure it's installed.")
    sys.exit(1)


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    parser = argparse.ArgumentParser(description="Dia TTS CLI for VANTA")
    parser.add_argument("--model", type=str, default="nari-labs/Dia-1.6B", help="Dia model identifier")
    parser.add_argument("--dtype", type=str, default="float16", help="Compute datatype for model loading")
    parser.add_argument("--script", type=str, required=True, help="Input script for TTS generation")
    parser.add_argument("--output", type=str, required=True, help="Path to save the generated audio file")
    parser.add_argument("--no-compile", action="store_true", dest="no_compile", help="Disable torch.compile if supported")
    args = parser.parse_args()

    logging.info(f"Loading model: {args.model} (dtype={args.dtype})")
    try:
        model = Dia.from_pretrained(args.model, compute_dtype=args.dtype)
    except Exception as e:
        logging.error(f"Failed to load Dia model: {e}", exc_info=True)
        sys.exit(1)

    generate_kwargs = {"verbose": True}
    if args.no_compile:
        generate_kwargs["use_torch_compile"] = False

    logging.info("Generating audio from script...")
    try:
        audio_data = model.generate(args.script, **generate_kwargs)
    except Exception as e:
        logging.error(f"Error during audio generation: {e}", exc_info=True)
        sys.exit(1)

    logging.info(f"Saving audio to {args.output}")
    try:
        model.save_audio(args.output, audio_data)
    except Exception as e:
        logging.error(f"Failed to save audio: {e}", exc_info=True)
        sys.exit(1)

    logging.info("Audio generation completed successfully.")


if __name__ == "__main__":
    main() 