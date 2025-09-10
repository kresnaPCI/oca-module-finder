import streamlit as st
import requests
import pandas as pd
import os

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

    def list_repos(self, org="OCA", max_pages=10):
        """Get all repos from OCA org (up to ~1000 repos)."""
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


# --- Cached functions ---
@st.cache_data(show_spinner=False)
def get_repos(token):
    gh = GitHubAPI(token)
    return gh.list_repos("OCA", max_pages=12)  # fetch all OCA repos (~1200+)


@st.cache_data(show_spinner=False)
def get_repo_modules(owner, repo, branch, token):
    """Return list of folders (modules) in repo branch."""
    gh = GitHubAPI(token)
    url = f"https://api.github.com/repos/{owner}/{repo}/contents?ref={branch}"
    data = gh.get(url)
    if not data:
        return []
    return [item["name"] for item in data if item["type"] == "dir"]


# --- Module checker ---
def check_modules(modules, target_version, token):
    repos = get_repos(token)
    results = {m: {"Available": "❌ No", "URL": "-"} for m in modules}

    for repo in repos:
        owner = repo["owner"]["login"]
        repo_name = repo["name"]

        # Get all module folders in one call
        repo_modules = get_repo_modules(owner, repo_name, target_version, token)
        if not repo_modules:
            continue

        for m in modules:
            if results[m]["Available"] == "✅ Yes":
                continue  # already found

            if m in repo_modules:
                results[m] = {
                    "Available": "✅ Yes",
                    "URL": f"https://github.com/{owner}/{repo_name}/tree/{target_version}/{m}"
                }

    # Convert dict → DataFrame
    df = pd.DataFrame([
        {"Module": m, "Available": results[m]["Available"], "URL": results[m]["URL"]}
        for m in modules
    ])
    return df


# --- Streamlit UI ---
st.title("🔎 OCA Module Availability Checker")
st.write("Check if OCA modules exist for a given Odoo version.")

modules_input = st.text_area("Modules (one per line)", "stock_picking_batch\nsale_order_type\naccount_invoice_import")
target_version = st.text_input("Odoo version", "18.0")
github_token = os.getenv("GITHUB_TOKEN")


if st.button("Check Modules"):
    module_list = [m.strip() for m in modules_input.splitlines() if m.strip()]
    if not module_list:
        st.warning("Please enter at least one module name.")
    else:
        with st.spinner("Checking modules... this may take some time for the first run."):
            df = check_modules(module_list, target_version, github_token)

        st.subheader("Results")
        st.dataframe(df, use_container_width=True)

        # CSV Export
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download CSV", data=csv, file_name="oca_module_check.csv", mime="text/csv")
