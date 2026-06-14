"""ARIA — private AI music module for the Private Internet platform.

Pipeline: user memories → Bedrock metadata (forced tool) → ElevenLabs music
generation → waveform computation → fal album art → S3/CloudFront.
All data is scoped by user_id; # MUST SCOPE BY USER.
"""
