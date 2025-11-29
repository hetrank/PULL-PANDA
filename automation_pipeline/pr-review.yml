
name: 🤖 PR Reviewer Bot

on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: read
  pull-requests: write
  issues: write

jobs:
  review:
    runs-on: ubuntu-latest

    steps:
     
      # 1) Checkout Repo (main repo where workflow is running)
      - name: Checkout bot repository
        uses: actions/checkout@v4

      # 2) Clone PROJECT REPO only once!
      - name: Clone target repository (project being reviewed)
        run: |
          echo "Cloning PR repository..."
          git clone https://github.com/${{ github.repository }} repo_clone
          echo "Repo cloned at: repo_clone"

      # 3) Set up Python
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.10"

      # 4) Install Dependencies
      - name: Install dependencies
        run: pip install -r requirements.txt

      # 5) Run Ingestion + PR reviewer
      - name: Run ingest + PR reviewer
        env:
          OWNER: ${{ github.repository_owner }}
          REPO: ${{ github.event.repository.name }}
          PR_NUMBER: ${{ github.event.pull_request.number }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
          PINECONE_API_KEY: ${{ secrets.PINECONE_API_KEY }}
          PINECONE_INDEX_NAME: ai
        run: |
          echo "Running ingest..."
          python "Version/RAG_Version 1.3/ingest.py"

          echo "Running PR reviewer..."
          python "Version/RAG_Version 1.3/iterative_prompt_selector.py"

      # 7) Cleanup
      - name: Clean up cloned repo
        run: |
          echo "Cleaning repo_clone..."
          rm -rf repo_clone
