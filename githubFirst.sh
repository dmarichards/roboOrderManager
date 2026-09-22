#!/usr/bin/env bash
echo ===============================================
echo First Time Update to create reporitories and push files to github
echo uses two inputs MESSAGE for the Commit, and REPO_NAME for the repository -- or the directory
if [ -z "$1" ]; then
    MESSAGE="Initial Update"
else
    MESSAGE="$1"
fi

if [ -z "$2" ]; then
    REPO_NAME=$(basename "$PWD")
else
    REPO_NAME="$2"
fi

echo Commit Message: "$MESSAGE"
echo Repository Name: "$REPO_NAME"


echo ===============================================
echo Done for each reporitory
git init
git branch -M main
git status

echo ===============================================
echo Move programs to GitHub repository, explicitly, or all less .gitignore using .
git add .
git status
git commit -m "$MESSAGE"

echo ===============================================
echo Now creating on GitHub Host
gh repo create "dmarichards/$REPO_NAME" --private --source . --remote origin --push
git remote -v

echo ===============================================
echo Github First time update complete