import streamlit as st
import requests
from urllib.parse import urlparse

# --- GitHub API helper ---
class GitHubAPI:
    def __init__(self, token=None):
        self.token = token

    def _get_headers(self):
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers

    def get(self, url, params=None):
        try:
            r = requests.get(url, headers=self._get_headers(), params=params, timeout=10)
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 404:
                return None
            else:
                st.warning(f"GitHub API error {r.status_code}: {r.text}")
                return None
        except Exception as e:
            st.error(f"Error fetching {url}: {e}")
            return None

    def check_branch_exists(self, owner, repo, branch):
        url = f"https://api.github.com/repos/{owner}/{repo}/branches/{branch}"
        return self.get(url) is not None

    def list_repos(self, org="OCA", max_pages=5):
        """Get list of repos from OCA org (limited pages for performance)."""
        repos = []
        for page in range(1, max_pages+1):
            url = f"https://api.github.com/orgs/{org}/repos?per_page=100&page={page}"
            data = self.get(url)
            if not data:
                break
            repos.extend(data)
            if len(data) < 100:
                break
        return repos


# --- OCA Module Checker ---
class OCAModuleChecker:
    def __init__(self, target_version="18.0", github_token=None):
        self.target_version = target_version
        self.github = GitHubAPI(token=github_token)

    def check_module(self, module_name):
        repos = self.github.list_repos("OCA", max_pages=5)  # can adjust pages if needed
        for repo in repos:
            owner = repo["owner"]["login"]
            repo_name = repo["name"]

            # Check branch exists
            if not self.github.check_branch_exists(owner, repo_name, self.target_version):
                continue

            # Check if module folder exists
            api_url = f"https://api.github.com/repos/{owner}/{repo_name}/contents/{module_name}?ref={self.target_version}"
            result = self.github.get(api_url)
            if result:
                return True, f"https://github.com/{owner}/{repo_name}/tree/{self.target_version}/{module_name}"

        return False, ""


# --- Streamlit UI ---
st.title("🔎 OCA Module Availability Checker")
st.write("Enter a list of **OCA module technical names** (one per line):")

modules_input = st.text_area("Modules", "stock_picking_batch\nsale_order_type")
target_version = st.text_input("Odoo version", "18.0")
github_token = st.text_input("GitHub Token (optional, recommended to avoid rate limits)", type="password")

if st.button("Check Modules"):
    module_list = [m.strip() for m in modules_input.splitlines() if m.strip()]
    if not module_list:
        st.warning("Please enter at least one module name.")
    else:
        checker = OCAModuleChecker(target_version, github_token)
        results = []

        progress = st.progress(0)
        for i, module in enumerate(module_list, start=1):
            available, url = checker.check_module(module)
            results.append({
                "Module": module,
                "Available": "✅ Yes" if available else "❌ No",
                "URL": url or "-"
            })
            progress.progress(i / len(module_list))

        st.subheader("Results")
        st.dataframe(results)
