# GitHub Actions CI

Automated checks run on pushes and pull requests:
- Dependency installation (`requirements.txt`)
- Automated unit test suite (`python -m unittest discover -s tests -v`)
- Python bytecode syntax verification (`python -m compileall -q bot.py gta_hub tests`)

