# Docker Image Tags Reference

## How Docker Image Tagging Works

The CI/CD pipeline uses `docker/metadata-action` to automatically generate Docker image tags based on what you push to GitHub.

## Two Different Scenarios

### Scenario 1: Push to `main` Branch (No Version Tag)

```bash
git add .
git commit -m "Fix bug"
git push origin main
```

**Result**: Images are tagged with branch name only:

```
ghcr.io/cyberdns/curio-backend:main
ghcr.io/cyberdns/curio-frontend:main
ghcr.io/cyberdns/curio:main
```

❌ **No version numbers** (1.0.0, 1.0, 1, etc.)

---

### Scenario 2: Push Version Tag (e.g., v1.0.0)

```bash
./version.sh bump patch        # Updates VERSION file
git add VERSION frontend/package.json
git commit -m "Bump version to 1.0.1"
git push origin main
./version.sh release           # Creates and pushes v1.0.1 tag
```

**Result**: Images are tagged with multiple version tags:

```
ghcr.io/cyberdns/curio-backend:1.0.1    ← Full version
ghcr.io/cyberdns/curio-backend:1.0      ← Major.minor
ghcr.io/cyberdns/curio-backend:1        ← Major only
ghcr.io/cyberdns/curio-backend:latest   ← Latest release
ghcr.io/cyberdns/curio-backend:main     ← Also has branch tag
```

✅ **All version tags are created!**

---

## Why This Matters

### For Deployment

```yaml
# Using version-specific tag (stable, won't change)
docker pull ghcr.io/cyberdns/curio-backend:1.0.1

# Using major version (gets latest 1.x.x)
docker pull ghcr.io/cyberdns/curio-backend:1

# Using latest (gets latest release)
docker pull ghcr.io/cyberdns/curio-backend:latest

# Using main branch (development, unstable)
docker pull ghcr.io/cyberdns/curio-backend:main
```

### Recommendation

- **Production**: Use specific version tags (e.g., `1.0.1`) or major version (`1`)
- **Testing**: Use `main` for latest development code
- **Avoid**: Using `latest` in production (unclear which version you're running)

---

## Complete Workflow Example

```bash
# 1. Develop your feature
git checkout -b feature/my-feature
# ... make changes ...
git commit -m "feat: add new feature"

# 2. Merge to main
git checkout main
git merge feature/my-feature
git push origin main
# → This creates ghcr.io/cyberdns/curio:main (no version tags)

# 3. Release a new version
./version.sh bump minor        # 1.0.0 → 1.1.0
git add VERSION frontend/package.json
git commit -m "chore: bump version to 1.1.0"
git push origin main

# 4. Create and push version tag
./version.sh release
# → This creates:
#   ghcr.io/cyberdns/curio:1.1.0
#   ghcr.io/cyberdns/curio:1.1
#   ghcr.io/cyberdns/curio:1
#   ghcr.io/cyberdns/curio:latest
```

---

## Checking Available Tags

### On GitHub Web UI

Visit: https://github.com/cyberdns?tab=packages

### Using GitHub API

```bash
# Backend images
curl -s "https://api.github.com/users/cyberdns/packages/container/curio-backend/versions" | \
  jq -r '.[].metadata.container.tags[]' | sort -V

# Frontend images
curl -s "https://api.github.com/users/cyberdns/packages/container/curio-frontend/versions" | \
  jq -r '.[].metadata.container.tags[]' | sort -V

# Unraid all-in-one
curl -s "https://api.github.com/users/cyberdns/packages/container/curio/versions" | \
  jq -r '.[].metadata.container.tags[]' | sort -V
```

### Using Docker

```bash
# This only works if you're authenticated
docker pull ghcr.io/cyberdns/curio-backend:1.0.0
docker images | grep curio-backend
```

---

## Quick Reference Table

| Git Action               | Trigger     | Docker Tags Created                   |
| ------------------------ | ----------- | ------------------------------------- |
| `git push origin main`   | Branch push | `main` only                           |
| `git push origin v1.0.0` | Version tag | `1.0.0`, `1.0`, `1`, `latest`, `main` |
| `git push origin v1.1.0` | Version tag | `1.1.0`, `1.1`, `1`, `latest`, `main` |
| `git push origin v2.0.0` | Version tag | `2.0.0`, `2.0`, `2`, `latest`, `main` |

**Key Takeaway**: Version-tagged images only exist when you push version tags!

---

## Common Mistakes

### ❌ Mistake 1: Forgetting to push the tag

```bash
./version.sh bump patch
git add VERSION frontend/package.json
git commit -m "Bump version"
git push origin main           # ← Missing tag push!
```

**Fix**: Use `./version.sh release` which automatically pushes the tag.

### ❌ Mistake 2: Expecting versions from main pushes

```bash
git push origin main
# Then expecting: ghcr.io/cyberdns/curio:1.0.0  ← Won't exist!
```

**Fix**: Only version tags create version-numbered images.

### ❌ Mistake 3: Using main images in production

```yaml
# Don't do this in production
image: ghcr.io/cyberdns/curio:main
```

**Fix**: Use version tags for stability:

```yaml
# Do this instead
image: ghcr.io/cyberdns/curio:1.0.0
```

---

## Summary

1. **Branch pushes** (`git push origin main`) → Only create `main` tag
2. **Version tags** (`git push origin v1.0.0`) → Create version tags: `1.0.0`, `1.0`, `1`, `latest`
3. Use `./version.sh release` to automatically push version tags
4. Check https://github.com/cyberdns?tab=packages to see published images
5. Use specific version tags in production, not `latest` or `main`
