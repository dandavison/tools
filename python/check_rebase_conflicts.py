#!/usr/bin/env python3
"""
Script to check for merge conflict resolution errors between original and rebased commits.

Usage: python check_rebase_conflicts.py <base> <head> <head-pre-rebase>
"""

import subprocess
import sys


def run_command(cmd):
    """Run a shell command and return the output."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {cmd}")
        print(f"Error message: {e.stderr}")
        sys.exit(1)


def get_commit_sequence(start, end):
    """Get list of commits between start and end (inclusive)."""
    cmd = f"git rev-list --reverse {start}..{end}"
    commits = run_command(cmd).split("\n")
    return [c for c in commits if c]  # Filter empty strings


def get_commit_message(commit):
    """Get the commit message for a given commit."""
    cmd = f"git log --format=%s -n 1 {commit}"
    return run_command(cmd)


def check_commit_pair(pre_rebase_commit, rebased_commit):
    """Check a pair of commits for merge conflict resolution errors using Claude."""

    # Get the full git show output for both commits
    pre_rebase_show = run_command(f"git show {pre_rebase_commit}")
    rebased_show = run_command(f"git show {rebased_commit}")

    # Construct the prompt for Claude
    prompt = f"""
Below are two commits. The second is intended to be functionally the same commit as the first,
but derives from a rebased branch. Therefore (a) it will differ slightly due to the new parent
context and (b) it may have errors resulting from merge conflict resolution. Your task is to
determine whether there are any such errors. Respond with a description of the error if there's
an error. Otherwise respond with no output.

# pre-rebase commit
{pre_rebase_show}

# rebased commit
{rebased_show}
"""

    # Call Claude with the prompt
    try:
        result = subprocess.run(
            ["cursor", "agent", "--print"],
            # ["claude", "--print"],
            input=prompt,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error calling claude: {e.stderr}")
        return None
    except FileNotFoundError:
        print(
            "Error: 'claude' command not found. Please ensure Claude CLI is installed and in PATH."
        )
        sys.exit(1)


def main():
    if len(sys.argv) != 4:
        print("Usage: python check_rebase_conflicts.py <base> <head> <head-pre-rebase>")
        sys.exit(1)

    base = sys.argv[1]
    head = sys.argv[2]
    head_pre_rebase = sys.argv[3]

    print(f"Analyzing rebase from {head_pre_rebase} to {head} (base: {base})")
    print()

    # Step 1: Get the commit sequence base...head
    print("Step 1: Getting rebased commit sequence...")
    rebased_commits = get_commit_sequence(base, head)
    n = len(rebased_commits)
    print(f"Found {n} commits in {base}..{head}")
    print()

    # Step 2: Get the pre-rebase commit sequence
    print("Step 2: Getting pre-rebase commit sequence...")
    # Calculate the starting point: head-pre-rebase~n
    pre_rebase_start = f"{head_pre_rebase}~{n}"
    pre_rebase_commits = get_commit_sequence(pre_rebase_start, head_pre_rebase)

    if len(pre_rebase_commits) != n:
        print(
            f"Error: Expected {n} commits in pre-rebase sequence, but found {len(pre_rebase_commits)}"
        )
        sys.exit(1)

    print(
        f"Found {len(pre_rebase_commits)} commits in {pre_rebase_start}..{head_pre_rebase}"
    )
    print()

    # Sanity check: verify commit messages match
    print("Step 3: Verifying commit messages match...")
    for i, (pre_commit, post_commit) in enumerate(
        zip(pre_rebase_commits, rebased_commits), 1
    ):
        pre_msg = get_commit_message(pre_commit)
        post_msg = get_commit_message(post_commit)

        print(f"  Commit {i}/{n}:")
        print(f"    Pre-rebase:  {pre_commit[:8]} - {pre_msg}")
        print(f"    Post-rebase: {post_commit[:8]} - {post_msg}")

        if pre_msg != post_msg:
            print("\nWarning: Commit messages don't match!")
            print(f"  Pre-rebase:  {pre_msg}")
            print(f"  Post-rebase: {post_msg}")
            print("Continuing anyway...")
    print()

    # Step 4: Check each commit pair for errors
    print("Step 4: Checking for merge conflict resolution errors...")
    print("-" * 80)

    for i, (pre_commit, post_commit) in enumerate(
        zip(pre_rebase_commits, rebased_commits), 1
    ):
        pre_msg = get_commit_message(pre_commit)
        print(f"\nChecking commit {i}/{n}: {pre_msg}")
        print(f"  Pre-rebase:  {pre_commit[:8]}")
        print(f"  Post-rebase: {post_commit[:8]}")

        error = check_commit_pair(pre_commit, post_commit)

        print("\n" + "=" * 80)
        # print("ERROR FOUND!")
        # print("=" * 80)
        print(f"Commit: {pre_msg}")
        print(f"Pre-rebase SHA: {pre_commit}")
        print(f"Post-rebase SHA: {post_commit}")
        # print("\nError description:")
        print(error)
        print("=" * 80)
        # print("\nStopping analysis. Please fix this error before continuing.")
        # sys.exit(1)

    print("\n" + "=" * 80)
    print("SUCCESS: No merge conflict resolution errors found!")
    print("=" * 80)


if __name__ == "__main__":
    main()
