import subprocess
import datetime


def commit_and_push(filename):

    subprocess.run(["git", "config", "--global", "user.name", "github-actions"], check=True)
    subprocess.run(["git", "config", "--global", "user.email", "actions@github.com"], check=True)

    subprocess.run(["git", "add", filename], check=True)
    subprocess.run(["git", "add", "menu_state.json"], check=True)

    result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)

    if result.stdout.strip() == "":
        print("No changes")
        return

    subprocess.run(
        ["git", "commit", "-m", f"Update {filename}"],
        check=True
    )

    subprocess.run(["git", "push"], check=True)


def main():

    today = datetime.date.today()

    filename = f"menu-{today.year}-{today.month:02d}.ics"

    commit_and_push(filename)


if __name__ == "__main__":
    main()
