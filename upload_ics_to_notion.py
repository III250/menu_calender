import subprocess
import glob

def commit_all():

    subprocess.run(["git", "config", "user.name", "github-actions"], check=True)

    subprocess.run(["git", "config", "user.email", "actions@github.com"], check=True)

    subprocess.run(["git", "add", "."], check=True)

    subprocess.run(
        ["git", "commit", "-m", "update menu and index"],
        check=False
    )

    subprocess.run(["git", "push"], check=True)


def main():

    commit_all()

    print("commit完了")


if __name__ == "__main__":
    main()
