import asyncio

from github import Github
from github.Repository import Repository
from utils import logger
log = logger.logger

class GitHubClient:
    _instance = None

    def __init__(self, access_token, orgList):
        self.client = Github(access_token)
        self.repos = {}

        self.bug_project = None
        self.feature_project = None

        for x in orgList:
            org = self.client.get_organization(x)
            for repo in org.get_repos("public"):  # build a method to access our repos
                print(f"Loaded repo {repo.full_name}")
                self.repos[repo.full_name] = repo
            for repo in org.get_repos("private"):  # build a method to access our repos
                print(f"Loaded repo {repo.full_name}")
                self.repos[repo.full_name] = repo

    @classmethod
    def initialize(cls, access_token, org=None):
        log.info("Initializing Github connection...")
        if org is None:
            orgList = ["lorddusk"]
        else:
            orgList = org
        if cls._instance:
            raise RuntimeError("Client already initialized")
        inst = cls(access_token, orgList)
        cls._instance = inst
        return inst

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            raise RuntimeError("Client not initialized")
        return cls._instance

    def get_repo(self, repo, default='CrawlerEmporium/5eCrawler'):
        return self.repos.get(repo, self.repos.get(default))

    async def create_issue(self, repo, title, description, labels=None):
        if labels is None:
            labels = []
        if not isinstance(repo, Repository):
            repo = self.get_repo(repo)

        def _():
            return repo.create_issue(title, description, labels=labels)

        return await asyncio.get_event_loop().run_in_executor(None, _)

    async def add_issue_comment(self, repo, issue_num, description):
        if not isinstance(repo, Repository):
            repo = self.get_repo(repo)

        def _():
            issue = repo.get_issue(issue_num)
            return issue.create_comment(description)

        return await asyncio.get_event_loop().run_in_executor(None, _)

    async def label_issue(self, repo, issue_num, labels):
        if not isinstance(repo, Repository):
            repo = self.get_repo(repo)

        def _():
            issue = repo.get_issue(issue_num)
            issue.edit(labels=labels)

        return await asyncio.get_event_loop().run_in_executor(None, _)

    async def close_issue(self, repo, issue_num, comment=None):
        if not isinstance(repo, Repository):
            repo = self.get_repo(repo)

        def _():
            issue = repo.get_issue(issue_num)
            if comment:
                issue.create_comment(comment)
            issue.edit(state="closed")

        return await asyncio.get_event_loop().run_in_executor(None, _)

    async def open_issue(self, repo, issue_num, comment=None):
        if not isinstance(repo, Repository):
            repo = self.get_repo(repo)

        def _():
            issue = repo.get_issue(issue_num)
            if comment:
                issue.create_comment(comment)
            issue.edit(state="open")

        return await asyncio.get_event_loop().run_in_executor(None, _)

    async def rename_issue(self, repo, issue_num, new_title):
        if not isinstance(repo, Repository):
            repo = self.get_repo(repo)

        def _():
            issue = repo.get_issue(issue_num)
            issue.edit(title=new_title)

        return await asyncio.get_event_loop().run_in_executor(None, _)

    async def edit_issue_body(self, repo, issue_num, new_body):
        if not isinstance(repo, Repository):
            repo = self.get_repo(repo)

        def _():
            issue = repo.get_issue(issue_num)
            issue.edit(body=new_body)

        return await asyncio.get_event_loop().run_in_executor(None, _)

    async def add_issue_to_project(self, issue_num, is_bug):

        def _():
            if is_bug:
                first_col = self.bug_project.get_columns()[0]
            else:
                first_col = self.feature_project.get_columns()[0]

            first_col.create_card(content_id=issue_num, content_type="Issue")

        return await asyncio.get_event_loop().run_in_executor(None, _)
