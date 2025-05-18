import subprocess
from pathlib import Path


class RepoManager:
    def __init__(self, project_config):
        def parse_bool(value):
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() == "yes"
            return False

        self.git_cloning_enabled = parse_bool(project_config.get("git_cloning_enabled", "No"))
        self.local_path_enabled = parse_bool(project_config.get("local_path_enabled", "No"))

        self.source_repo_url = project_config.get("source_repo_url")
        self.source_branch = project_config.get("source_branch")
        self.target_repo_url = project_config.get("target_repo_url")
        self.target_branch = project_config.get("target_branch")

        self.source_path = Path(project_config.get("source_path", "source_project")).resolve()
        self.target_path = Path(project_config.get("target_path", "target_project")).resolve()

    def clone_repo(self, repo_url, branch, dest_path):
        if not dest_path.exists():
            print(f"🔄 Cloning {repo_url} [branch: {branch}] into {dest_path}...")
            subprocess.run(['git', 'clone', '-b', branch, repo_url, str(dest_path)], check=True)
        else:
            print(f"⚡ Repo already exists at {dest_path}, pulling latest changes...")
            subprocess.run(['git', '-C', str(dest_path), 'pull'], check=True)

    def checkout_branch(self, repo_path, branch):
        subprocess.run(['git', '-C', str(repo_path), 'checkout', branch], check=True)

    def prepare_repos(self):
        if self.git_cloning_enabled:
            self.clone_repo(self.source_repo_url, self.source_branch, self.source_path)
            self.clone_repo(self.target_repo_url, self.target_branch, self.target_path)
            self.checkout_branch(self.source_path, self.source_branch)
            self.checkout_branch(self.target_path, self.target_branch)
        elif self.local_path_enabled:
            print(f"📁 Using local source path: {self.source_path}")
            print(f"📁 Using local target path: {self.target_path}")
            if not self.source_path.exists():
                raise FileNotFoundError(f"❌ Source path not found: {self.source_path}")
            if not self.target_path.exists():
                raise FileNotFoundError(f"❌ Target path not found: {self.target_path}")
        else:
            raise ValueError(
                "❌ Either git_cloning_enabled or local_path_enabled must be set to 'Yes' in migration_map.yaml")

    def get_source_path(self):
        return self.source_path

    def get_target_path(self):
        return self.target_path
