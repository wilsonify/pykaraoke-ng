# SonarQube Integration Setup

[← Back to Home](../index.md) | [Developer Guide](../developers.md)

---

This repository is configured to use SonarCloud for continuous code quality analysis.

## Prerequisites

- GitHub repository with Actions enabled
- SonarCloud account connected to your GitHub organization

## Setup Instructions

### 1. Configure GitHub Secrets

Add the following secrets to your GitHub repository:

1. Go to your repository: https://github.com/wilsonify/pykaraoke-ng
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **"New repository secret"** for each of the following:

#### SONARQUBE_TOKEN
- **Name:** `SONARQUBE_TOKEN`
- **Value:** Your SonarCloud token (provided separately for security)
- **Description:** Authentication token for SonarCloud API access

#### SONARQUBE_HOST_URL
- **Name:** `SONARQUBE_HOST_URL`
- **Value:** `https://sonarcloud.io`
- **Description:** SonarCloud server URL

### 2. Verify Configuration Files

The repository includes the following SonarQube configuration files:

- **`sonar-project.properties`** - Project configuration for SonarCloud
- **`.github/workflows/sonarqube.yml`** - GitHub Actions workflow for automated analysis

### 3. Trigger Analysis

SonarCloud analysis runs automatically on:
- Push to `master`, `main`, or `develop` branches
- Pull request events (opened, synchronized, reopened)

To manually trigger an analysis:
1. Go to **Actions** tab in GitHub
2. Select **"SonarQube Analysis"** workflow
3. Click **"Run workflow"**

## Viewing Results

After the workflow completes:

1. Visit your SonarCloud project dashboard:
   - URL: https://sonarcloud.io/project/overview?id=wilsonify_pykaraoke-ng

2. Review quality metrics:
   - **Bugs**: Potential runtime errors
   - **Vulnerabilities**: Security issues
   - **Code Smells**: Maintainability issues
   - **Coverage**: Test coverage percentage
   - **Duplications**: Duplicated code blocks

## Quality Gates

The project is configured with quality gates that must pass:
- No new critical or blocker issues
- No new security vulnerabilities
- Maintain or improve coverage on new code
- Keep technical debt ratio in check

If quality gates fail, the CI pipeline will fail, preventing merges.

## Troubleshooting

### Authentication Errors
- Verify `SONARQUBE_TOKEN` is correctly set in GitHub Secrets
- Check token has not expired in SonarCloud

### Analysis Failures
- Check workflow logs in GitHub Actions
- Verify `sonar-project.properties` syntax
- Ensure all Python files are syntactically correct

### Quality Gate Failures
- Review specific issues in SonarCloud dashboard
- Fix reported issues in code
- Re-run analysis after fixes

## Security Note

**NEVER** commit the SonarQube token directly to the repository. Always use GitHub Secrets to store sensitive credentials.
