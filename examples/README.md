# Examples

This directory contains example outputs and documentation for FaceTrace.

## Files

- `example_evidence.json` — Example evidence record output
- `pipeline_diagram.txt` — ASCII diagram of the pipeline flow
- `demo_output.txt` — Example terminal output for a successful run

## Quick Demo

```bash
# Run the pipeline with a sample image
python run.py --image your_image.jpg

# Verify the generated evidence
python verify.py --evidence evidence_*.json
```

## Example Evidence Record

```json
{
  "input_image_hash": "a1b2c3d4e5f67890...",
  "matched_url": "https://instagram.com/p/EXAMPLE/",
  "platform": "Instagram",
  "face_similarity": 0.87,
  "verification_threshold": 0.75,
  "verification_status": "MATCH",
  "timestamp": "2026-09-04T12:34:56Z",
  "evidence_hash": "8f31a7c9...e921"
}
```

## Notes

- Real social media URLs are discovered dynamically via reverse image search
- URLs shown in examples are for illustration only
- The actual pipeline will discover real URLs based on the input image
