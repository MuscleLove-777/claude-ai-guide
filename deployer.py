"""Claude AI完全ガイド - GitHub Pagesデプロイモジュール（スタンドアロン版）

blog_engineの共通モジュールを使用し、フォールバックとしてローカル実装を持つ。
"""
import sys
from pathlib import Path

_engine_path = str(Path(__file__).parent.parent)
if _engine_path not in sys.path:
    sys.path.insert(0, _engine_path)

try:
    from blog_engine.deployer import GitHubPagesDeployer
except ImportError:
    import logging
    import subprocess
    from datetime import datetime

    logger = logging.getLogger(__name__)

    class GitHubPagesDeployer:
        """GitHub Pagesへのデプロイ（スタンドアロン版）"""

        def __init__(self, config):
            self.config = config
            self.site_dir = getattr(config, "SITE_DIR", Path(config.BASE_DIR) / "output" / "site")
            self.repo = config.GITHUB_REPO
            self.branch = getattr(config, "GITHUB_BRANCH", "gh-pages")
            self.token = getattr(config, "GITHUB_TOKEN", "")

            if not self.repo:
                raise ValueError("GITHUB_REPO が設定されていません。")

        def deploy(self) -> dict:
            if not self.site_dir.exists():
                return {"status": "error", "message": "サイトディレクトリが見つかりません。"}

            try:
                self._run_git_commands()
                username = self.repo.split("/")[0]
                repo_name = self.repo.split("/")[1]
                url = f"https://{username}.github.io/{repo_name}/"
                return {"status": "success", "message": "デプロイ完了", "url": url}
            except subprocess.CalledProcessError as e:
                return {"status": "error", "message": f"デプロイ失敗: {e.stderr or e}"}
            except Exception as e:
                return {"status": "error", "message": f"エラー: {e}"}

        def _run_git_commands(self):
            site_dir = str(self.site_dir)
            remote_url = (
                f"https://{self.token}@github.com/{self.repo}.git"
                if self.token
                else f"https://github.com/{self.repo}.git"
            )

            def run(cmd, cwd=site_dir):
                result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, shell=True)
                if result.returncode != 0:
                    raise subprocess.CalledProcessError(result.returncode, cmd, stderr=result.stderr)
                return result.stdout

            git_dir = self.site_dir / ".git"
            if not git_dir.exists():
                run("git init")
                run(f"git remote add origin {remote_url}")
            else:
                run(f"git remote set-url origin {remote_url}")

            run(f"git checkout -B {self.branch}")
            run("git add -A")

            try:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                run(f'git commit -m "サイト更新: {now}"')
            except subprocess.CalledProcessError:
                return

            run(f"git push -f origin {self.branch}")

        def check_status(self) -> dict:
            username = self.repo.split("/")[0] if "/" in self.repo else ""
            repo_name = self.repo.split("/")[1] if "/" in self.repo else ""
            return {
                "repo": self.repo,
                "branch": self.branch,
                "site_dir": str(self.site_dir),
                "site_exists": self.site_dir.exists(),
                "url": f"https://{username}.github.io/{repo_name}/" if username else "未設定",
                "token_configured": bool(self.token),
            }
