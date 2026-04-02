"""Git repository cloning functionality."""

import os
import subprocess
from pathlib import Path


def get_repo_url() -> str:
    """Read GIT_REPO environment variable."""
    repo_url = os.environ.get("GIT_REPO")
    if not repo_url:
        raise ValueError("GIT_REPO environment variable is not set")
    return repo_url


def get_repos_dir() -> Path:
    """Get the repos directory path."""
    return Path("/app/repos")


def clone_repository(repo_url: str | None = None, target_dir: Path | None = None) -> Path:
    """Clone a git repository.
    
    Args:
        repo_url: Git repository URL. If None, reads from GIT_REPO env var.
        target_dir: Target directory for cloning. If None, uses /app/repos.
        
    Returns:
        Path to the cloned repository.
    """
    if repo_url is None:
        repo_url = get_repo_url()
    
    if target_dir is None:
        target_dir = get_repos_dir()
    
    # Create repos directory if it doesn't exist
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract repo name from URL
    repo_name = repo_url.rstrip("/").split("/")[-1]
    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]
    
    clone_path = target_dir / repo_name
    
    if clone_path.exists():
        print(f"Repository already exists at {clone_path}")
        return clone_path
    
    print(f"Cloning {repo_url} into {clone_path}...")
    
    result = subprocess.run(
        ["git", "clone", repo_url, str(clone_path)],
        capture_output=True,
        text=True,
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"Git clone failed: {result.stderr}")
    
    print(f"Successfully cloned to {clone_path}")
    return clone_path
