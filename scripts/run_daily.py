import argparse
import datetime
import subprocess
import shlex
import sys
from pathlib import Path

def run_command(cmd: str):
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"Error failed cmd: {cmd}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Run daily pipeline")
    parser.add_argument("--question", type=str, default="What is the most interesting tension in today's notes?", help="Insight question")
    parser.add_argument("--content", type=str, default="Create a strong insight-based post from today's notes", help="Content prompt")
    args = parser.parse_args()

    today = datetime.datetime.now().strftime("%Y-%m-%d")
    print(f"Running pipeline for: {today}")
    
    print("Starting daily pipeline")

    scripts_dir = Path(__file__).resolve().parent

    print("Compiling knowledge...")
    run_command(f"{sys.executable} {scripts_dir / 'compile_wiki.py'}")

    print("Building index...")
    run_command(f"{sys.executable} {scripts_dir / 'build_index.py'}")

    print("Asking insight question...")
    question_quoted = shlex.quote(args.question)
    run_command(f"{sys.executable} {scripts_dir / 'ask.py'} {question_quoted}")

    print("Generating content...")
    content_quoted = shlex.quote(args.content)
    run_command(f"{sys.executable} {scripts_dir / 'generate_content.py'} {content_quoted}")

    print("Pipeline complete")
    print("Daily AI Brain pipeline completed successfully")

if __name__ == "__main__":
    main()
