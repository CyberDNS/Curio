#!/bin/bash
# Version management script for Curio

set -e

VERSION_FILE="VERSION"
CURRENT_VERSION=$(cat $VERSION_FILE)

show_current() {
    echo "📦 Current version: v$CURRENT_VERSION"
    echo ""
    echo "Git tags:"
    git tag -l "v*" | tail -5 || echo "  No version tags yet"
    echo ""
    echo "Latest commit:"
    git log -1 --oneline
}

bump_version() {
    local bump_type=$1
    
    # Parse current version
    IFS='.' read -r major minor patch <<< "$CURRENT_VERSION"
    
    case $bump_type in
        major)
            major=$((major + 1))
            minor=0
            patch=0
            ;;
        minor)
            minor=$((minor + 1))
            patch=0
            ;;
        patch)
            patch=$((patch + 1))
            ;;
        *)
            echo "❌ Invalid bump type. Use: major, minor, or patch"
            exit 1
            ;;
    esac
    
    NEW_VERSION="$major.$minor.$patch"
    
    echo "🔄 Bumping version: $CURRENT_VERSION → $NEW_VERSION"
    echo ""
    
    # Update VERSION file
    echo "$NEW_VERSION" > $VERSION_FILE
    
    # Update frontend package.json
    if [ -f "frontend/package.json" ]; then
        sed -i.bak "s/\"version\": \".*\"/\"version\": \"$NEW_VERSION\"/" frontend/package.json
        rm frontend/package.json.bak
        echo "✅ Updated frontend/package.json"
    fi
    
    # Update backend if you have a setup.py or pyproject.toml
    # (Add similar logic here if needed)
    
    echo "✅ Updated VERSION file"
    echo ""
    echo "📝 Next steps:"
    echo "   1. Review changes: git diff"
    echo "   2. Commit: git add . && git commit -m 'Bump version to $NEW_VERSION'"
    echo "   3. Tag: git tag -a v$NEW_VERSION -m 'Release v$NEW_VERSION'"
    echo "   4. Push: git push origin main --tags"
}

create_release() {
    local version=$1
    
    if [ -z "$version" ]; then
        version="v$CURRENT_VERSION"
    fi
    
    # Check if version is already tagged
    if git rev-parse "$version" >/dev/null 2>&1; then
        echo "❌ Tag $version already exists!"
        exit 1
    fi
    
    echo "🚀 Creating release: $version"
    echo ""
    
    # Create annotated tag
    git tag -a "$version" -m "Release $version"
    
    echo "✅ Tag created: $version"
    echo ""
    echo "📤 Pushing tag to remote..."
    git push origin "$version"
    
    echo "✅ Tag pushed successfully!"
    echo ""
    echo "🤖 GitHub Actions will now:"
    echo "   ✓ Run all tests"
    echo "   ✓ Build Docker images with version tags:"
    echo "     • ghcr.io/cyberdns/curio-backend:${version#v}"
    echo "     • ghcr.io/cyberdns/curio-frontend:${version#v}"
    echo "     • ghcr.io/cyberdns/curio:${version#v}"
    echo "   ✓ Also create tags: ${version%.*}, ${version%%.*}, latest"
    echo ""
    echo "🔍 Track progress at:"
    echo "   https://github.com/cyberdns/curio/actions"
}

show_help() {
    cat << EOF
📦 Curio Version Management

Usage: ./scripts/version.sh [command]

Commands:
    current             Show current version and tags
    bump <type>         Bump version (major|minor|patch)
    release [version]   Create release tag (defaults to current VERSION)
    help                Show this help message

Examples:
    ./version.sh current
    ./version.sh bump patch     # 1.0.0 → 1.0.1
    ./version.sh bump minor     # 1.0.0 → 1.1.0
    ./version.sh bump major     # 1.0.0 → 2.0.0
    ./version.sh release        # Create tag from VERSION file
    ./version.sh release v1.0.1 # Create specific tag

Workflow:
    1. Make changes and commit
    2. Run: ./version.sh bump patch
    3. Review and commit version changes
    4. Run: ./version.sh release
    5. Push: git push origin main --tags

EOF
}

# Main command handler
case "${1:-help}" in
    current)
        show_current
        ;;
    bump)
        bump_version "$2"
        ;;
    release)
        create_release "$2"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "❌ Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
