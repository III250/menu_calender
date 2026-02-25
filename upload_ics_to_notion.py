import subprocess
import glob


def commit():

    subprocess.run(["git", "config", "user.name", "github-actions"])
    subprocess.run(["git", "config", "user.email", "actions@github.com"])

    subprocess.run(["git", "add", "."])

    result = subprocess.run(
        ["git", "commit", "-m", "update menu"],
        capture_output=True,
        text=True
    )

    if "nothing to commit" in result.stdout:
        print("commitなし")
        return

    subprocess.run(["git", "push"])


def main():

    commit()

    print("upload complete")


if __name__ == "__main__":
    main()
