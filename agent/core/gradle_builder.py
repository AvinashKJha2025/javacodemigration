import subprocess


class GradleBuilder:
    def __init__(self, project_path):
        self.project_path = project_path

    def build(self):
        try:
            result = subprocess.run(["./gradlew", "build"], cwd=self.project_path, capture_output=True, text=True)
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, str(e)
