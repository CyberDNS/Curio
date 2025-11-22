# Version Management Guide

## Current Version

The current version is always stored in the `VERSION` file at the project root:

```bash
cat VERSION
# Output: 1.0.0
```

## Best Practices

### 1. **Semantic Versioning (SemVer)**

Use `MAJOR.MINOR.PATCH` format:

- **MAJOR** (2.0.0): Breaking changes, incompatible API changes
- **MINOR** (1.1.0): New features, backwards compatible
- **PATCH** (1.0.1): Bug fixes, backwards compatible

### 2. **Version Files**

Keep version synchronized across:

- ✅ `VERSION` - Single source of truth
- ✅ `frontend/package.json` - Frontend version
- ✅ Git tags - `v1.0.0` format

### 3. **Development Workflow**

#### Option A: Using the Version Script (Recommended)

```bash
# Check current version
./version.sh current

# Bump version (updates VERSION + package.json)
./version.sh bump patch   # 1.0.0 → 1.0.1
./version.sh bump minor   # 1.0.0 → 1.1.0
./version.sh bump major   # 1.0.0 → 2.0.0

# Commit version changes
git add VERSION frontend/package.json
git commit -m "Bump version to 1.0.1"

# Create release tag
./version.sh release

# Push everything
git push origin main --tags
```

#### Option B: Manual Process

```bash
# 1. Update VERSION file
echo "1.0.1" > VERSION

# 2. Update frontend/package.json
# Edit "version": "1.0.1"

# 3. Commit
git add VERSION frontend/package.json
git commit -m "Bump version to 1.0.1"

# 4. Create tag
git tag -a v1.0.1 -m "Release v1.0.1"

# 5. Push
git push origin main --tags
```

## Release Process

### Complete Release Workflow

```bash
# 1. Ensure you're on main and up to date
git checkout main
git pull

# 2. Run tests locally
./run-tests.sh

# 3. Bump version
./version.sh bump patch

# 4. Update CHANGELOG (see below)
vim CHANGELOG.md

# 5. Commit version bump
git add VERSION frontend/package.json CHANGELOG.md
git commit -m "Release v1.0.1"

# 6. Create annotated tag
git tag -a v1.0.1 -m "Release v1.0.1 - Bug fixes and improvements"

# 7. Push commits and tags
git push origin main
git push origin v1.0.1

# 8. GitHub Actions will automatically:
#    - Run all tests
#    - Build Docker images
#    - Tag images: v1.0.1, v1.0, v1, latest
#    - Publish to ghcr.io
```

### What Gets Published

When you push a version tag like `v1.0.1`, the GitHub Actions workflow automatically creates multiple Docker image tags:

```
ghcr.io/cyberdns/curio-backend:1.0.1    # Exact version (no 'v' prefix)
ghcr.io/cyberdns/curio-backend:1.0      # Major.minor
ghcr.io/cyberdns/curio-backend:1        # Major only
ghcr.io/cyberdns/curio-backend:latest   # Latest stable
ghcr.io/cyberdns/curio-backend:main     # Also tagged with branch name

ghcr.io/cyberdns/curio-frontend:1.0.1
ghcr.io/cyberdns/curio-frontend:1.0
ghcr.io/cyberdns/curio-frontend:1
ghcr.io/cyberdns/curio-frontend:latest

ghcr.io/cyberdns/curio:1.0.1            # Unraid all-in-one
ghcr.io/cyberdns/curio:1.0
ghcr.io/cyberdns/curio:1
ghcr.io/cyberdns/curio:latest
```

**Note**: Version tags in Docker images do NOT have the 'v' prefix. Git tags use `v1.0.1`, but Docker images use `1.0.1`.

## Changelog Management

### Keep a CHANGELOG.md

```markdown
# Changelog

All notable changes to this project will be documented in this file.

## [1.0.1] - 2025-11-22

### Fixed

- Fixed RSS feed parsing for dates
- Corrected authentication token expiry

### Changed

- Updated dependencies

## [1.0.0] - 2025-11-20

### Added

- Initial stable release
- Full test suite with 80 tests
- Docker image publishing
```

### When to Update

- **Before releasing** - Document all changes since last release
- **Keep it organized** - Group by Added, Changed, Fixed, Removed
- **Link to PRs/Issues** - Reference GitHub issues when relevant

## Checking Versions

### Current Development Version

```bash
# Quick check
cat VERSION

# Full info
./version.sh current
```

### Published Versions

```bash
# List all tags
git tag -l "v*"

# Latest tag
git describe --tags --abbrev=0

# Check what's published on GitHub
gh release list  # If you have GitHub CLI
```

### Docker Image Versions

```bash
# List available tags (requires GitHub API)
curl -s https://api.github.com/users/cyberdns/packages/container/curio-backend/versions | jq -r '.[].metadata.container.tags[]' | sort -V
```

## Pre-releases

For beta/RC versions, use pre-release tags:

```bash
# Beta release
echo "1.1.0-beta.1" > VERSION
git tag v1.1.0-beta.1 -m "Beta release 1.1.0-beta.1"

# Release candidate
echo "1.1.0-rc.1" > VERSION
git tag v1.1.0-rc.1 -m "Release candidate 1.1.0-rc.1"

# Final release
echo "1.1.0" > VERSION
git tag v1.1.0 -m "Release 1.1.0"
```

## Branch Strategy

### Main Branch

- Always deployable
- Only merged from PRs
- Tagged for releases

### Feature Branches

- Branch from main: `feature/new-feature`
- Develop and test
- PR to main
- No version bumps until merged

### Release Flow

```
feature/add-feature  →  PR  →  main  →  Tag v1.1.0  →  Docker Images
```

## Automation

### GitHub Actions Auto-versioning (Future Enhancement)

You can automate version bumping with conventional commits:

```bash
# Commits that trigger version bumps
fix: Fixed bug          # → Patch (1.0.0 → 1.0.1)
feat: New feature       # → Minor (1.0.0 → 1.1.0)
feat!: Breaking change  # → Major (1.0.0 → 2.0.0)
```

Tools for this:

- `semantic-release`
- `standard-version`
- GitHub Actions with conventional commits

## Quick Reference

```bash
# View current version
cat VERSION

# Version script commands
./version.sh current              # Show version info
./version.sh bump patch          # Bug fix release
./version.sh bump minor          # Feature release
./version.sh bump major          # Breaking change
./version.sh release             # Create git tag

# Manual version commands
echo "1.0.1" > VERSION                   # Update version
git tag -a v1.0.1 -m "Release v1.0.1"   # Create tag
git push origin main --tags              # Publish

# Check published versions
git tag -l "v*"                          # Local tags
git ls-remote --tags origin              # Remote tags
docker pull ghcr.io/cyberdns/curio-backend:latest  # Latest image
```

## Rollback

If you need to rollback:

```bash
# Revert to previous version
git revert <commit-hash>
git push origin main

# Or checkout previous tag
git checkout v1.0.0
./version.sh release v1.0.2  # Re-release as patch
```

## Version in Application

### Backend (Python)

Add to `backend/app/__init__.py`:

```python
__version__ = "1.0.0"

# Or read from file
import os
VERSION_FILE = os.path.join(os.path.dirname(__file__), "../../VERSION")
with open(VERSION_FILE) as f:
    __version__ = f.read().strip()
```

### Frontend (React)

Add to `frontend/src/version.ts`:

```typescript
export const VERSION = "1.0.0";

// Or use package.json
import packageJson from "../package.json";
export const VERSION = packageJson.version;
```

### API Endpoint

Expose version via API:

```python
@app.get("/api/version")
def get_version():
    return {"version": __version__}
```

## Troubleshooting

### "My Docker images only have 'latest' and 'main' tags, not version numbers"

**Problem**: You pushed commits to `main` but didn't push a version tag.

**Solution**: The CI/CD workflow only creates version-tagged images when you push **version tags** (e.g., `v1.0.0`).

```bash
# Wrong: This only creates 'main' and 'latest' tags
git push origin main

# Right: This creates version tags (1.0.0, 1.0, 1, latest)
./version.sh release  # This pushes the version tag
```

### "How do I check what Docker images exist?"

```bash
# View on GitHub
# Go to: https://github.com/cyberdns?tab=packages

# Or use the GitHub API
curl -s "https://api.github.com/users/cyberdns/packages/container/curio-backend/versions" | \
  jq -r '.[].metadata.container.tags[]' | sort -V
```

### "The workflow runs but doesn't publish images"

Check:

1. GitHub Actions has write permissions to packages
2. You're authenticated to ghcr.io (done automatically in workflows)
3. The workflow completed successfully (check Actions tab)

## Summary

**Before every release:**

1. ✅ Run tests locally
2. ✅ Update VERSION file (`./version.sh bump patch`)
3. ✅ Update CHANGELOG.md
4. ✅ Commit version changes
5. ✅ Push commits: `git push origin main`
6. ✅ Create and push tag: `./version.sh release` (automatically pushes tag)
7. ✅ Verify Docker images published at https://github.com/cyberdns?tab=packages
8. ✅ Create GitHub release (optional)

**Key Point**: Version-tagged Docker images are ONLY created when you push version tags (via `./version.sh release`), not when you push to main.

The `version.sh` tool automates most of this!
