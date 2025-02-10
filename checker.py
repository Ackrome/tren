import git

def get_git_diff(repo_path):
    repo = git.Repo(repo_path)
    diff = repo.git.diff()
    return diff

# Пример использования
repo_path = r'C:\Users\ivant\Desktop\tren'
diff = get_git_diff(repo_path)
print(git.Repo(repo_path))
print(diff)
