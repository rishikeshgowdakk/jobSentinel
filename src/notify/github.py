import subprocess
from src.core.logger import logger

class GithubClient:
    def push_changes(self, job_title: str, company: str):
        try:
            # Stage changes
            subprocess.run(['git', 'add', '.'], check=True)
            
            # Commit
            commit_message = f"Applied to {job_title} at {company}"
            subprocess.run(['git', 'commit', '-m', commit_message], check=True)
            
            # Push
            subprocess.run(['git', 'push'], check=True)
            
            logger.info(f"Successfully pushed changes to GitHub for {job_title}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to push to GitHub: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during GitHub push: {e}")
