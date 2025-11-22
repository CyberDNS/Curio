from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.tag import Tag
from app.models.user import User
from app.schemas.tag import Tag as TagSchema, TagCreate, TagUpdate
from openai import AsyncOpenAI
from app.core.config import settings
import logging
import json

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=List[TagSchema])
def get_tags(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Get all tags for the current user."""
    tags = db.query(Tag).filter(Tag.user_id == current_user.id).order_by(Tag.name).all()
    return tags


@router.post("/", response_model=TagSchema)
def create_tag(
    tag: TagCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new tag for the current user."""
    # Normalize tag name
    tag_name = tag.name.strip().lower()

    existing = (
        db.query(Tag)
        .filter(Tag.name == tag_name, Tag.user_id == current_user.id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Tag with this name already exists")

    db_tag = Tag(name=tag_name, user_id=current_user.id)
    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)
    return db_tag


@router.put("/{tag_id}", response_model=TagSchema)
def update_tag(
    tag_id: int,
    tag_update: TagUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a tag for the current user."""
    tag = db.query(Tag).filter(Tag.id == tag_id, Tag.user_id == current_user.id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    if tag_update.name:
        # Normalize tag name
        new_name = tag_update.name.strip().lower()

        # Check if new name conflicts with existing tag
        existing = (
            db.query(Tag)
            .filter(
                Tag.name == new_name, Tag.user_id == current_user.id, Tag.id != tag_id
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=400, detail="Tag with this name already exists"
            )

        tag.name = new_name

    db.commit()
    db.refresh(tag)
    return tag


@router.delete("/{tag_id}")
def delete_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a tag for the current user."""
    tag = db.query(Tag).filter(Tag.id == tag_id, Tag.user_id == current_user.id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    db.delete(tag)
    db.commit()
    return {"message": "Tag deleted successfully"}


@router.post("/merge")
def merge_tags(
    source_tag_id: int,
    target_tag_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Merge source tag into target tag. Updates all articles and deletes source tag."""
    from app.models.article import Article

    # Verify both tags exist and belong to user
    source_tag = (
        db.query(Tag)
        .filter(Tag.id == source_tag_id, Tag.user_id == current_user.id)
        .first()
    )
    target_tag = (
        db.query(Tag)
        .filter(Tag.id == target_tag_id, Tag.user_id == current_user.id)
        .first()
    )

    if not source_tag:
        raise HTTPException(status_code=404, detail="Source tag not found")
    if not target_tag:
        raise HTTPException(status_code=404, detail="Target tag not found")
    if source_tag_id == target_tag_id:
        raise HTTPException(status_code=400, detail="Cannot merge tag with itself")

    # Find all articles with source tag
    # Use PostgreSQL JSON array contains operator @>
    from sqlalchemy import cast, type_coerce
    from sqlalchemy.dialects.postgresql import JSONB

    articles = (
        db.query(Article)
        .filter(
            Article.user_id == current_user.id,
            cast(Article.tags, JSONB).contains(cast([source_tag.name], JSONB)),
        )
        .all()
    )

    # Replace source tag with target tag in all articles
    for article in articles:
        if article.tags and source_tag.name in article.tags:
            # Remove source tag
            article.tags = [t for t in article.tags if t != source_tag.name]
            # Add target tag if not already present
            if target_tag.name not in article.tags:
                article.tags.append(target_tag.name)

    # Delete source tag
    db.delete(source_tag)
    db.commit()

    return {
        "message": f"Merged tag '{source_tag.name}' into '{target_tag.name}'",
        "articles_updated": len(articles),
    }


@router.post("/auto-merge")
async def auto_merge_tags(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Use LLM to identify and merge similar tags automatically."""
    from app.models.article import Article

    # Get all tags for the user
    tags = db.query(Tag).filter(Tag.user_id == current_user.id).order_by(Tag.name).all()

    if len(tags) < 2:
        return {
            "message": "Not enough tags to merge",
            "merges_performed": 0,
            "tags_merged": [],
        }

    # Prepare tag list for LLM
    tag_names = [tag.name for tag in tags]

    # Ask LLM to identify similar tags
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    system_prompt = """You are a tag management assistant. Your job is to consolidate tags to reduce overall tag count while maintaining meaningful categorization.

Analyze the provided tags and aggressively merge tags that belong to the same domain or topic area. The goal is to have FEWER, MORE GENERAL tags rather than many specific tags.

**TARGET TAG SELECTION:**
You can EITHER use an existing tag as the target OR create a new, more general tag name when it makes sense:
- **Use existing tag:** If one of the existing tags is already general enough (e.g., "python" exists and you want to merge "django", "flask" into it)
- **Create new tag:** If multiple specific tags should be consolidated into a broader category that doesn't exist yet (e.g., "ai-startup" + "artificial-intelligence" → "artificial-intelligence" or "ai")

**AGGRESSIVE MERGE GUIDELINES:**

1. **Merge different spellings/abbreviations:**
   - If you see "AI", "artificial-intelligence", "ai-technology" → use "artificial-intelligence" or create "ai" as target
   - If you see "ML", "machine-learning" → use "machine-learning" or create "ml" as target

2. **Merge plural/singular forms:**
   - If you see "startup", "startups" → use "startup" as target
   - If you see "python", "pythons" → use "python" as target

3. **Merge domain-specific terms into broader category:**
   - If you see "python", "django", "flask", "fastapi" → use "python" as target
   - If you see "react", "vue", "angular" without "frontend" → create "frontend" as target
   - If you see "docker", "kubernetes", "containers" → use "containers" or create more general term

4. **Merge related sub-topics into main topic:**
   - If you see "ai-startup", "tech-startup", "startup" → use "startup" as target
   - If you see "machine-learning", "deep-learning", "neural-networks" → use "machine-learning" or create "ai" as target
   - Prefer using existing general tags when available, create new ones when the existing options are all too specific

5. **Merge industry-specific terms:**
   - Create broader category tags when multiple industry terms exist
   - Example: "e-commerce", "online-shopping", "retail" → "commerce" or "retail"

6. **General principle:**
   - Choose the most general/broad tag name as target (existing or new)
   - Prefer simple, clear tag names over complex ones
   - Use existing tags when they're general enough
   - Create new tags when existing ones are all too specific
   - All other related tags become sources

**Target Selection Priority:**
1. If an existing tag is general enough → use it
2. If all existing tags are specific → create a new, more general tag
3. Prefer full words over abbreviations for new tags
4. Use lowercase, hyphenated format for new tags (e.g., "artificial-intelligence", not "Artificial Intelligence")

**Be AGGRESSIVE:** Aim to reduce the total number of tags by at least 30-50%. It's better to have fewer, more useful tags than many overlapping specific ones.

Respond with JSON:
{
  "merges": [
    {
      "target": "tag-name-existing-or-new",
      "sources": ["tag-1", "tag-2", "tag-3"]
    }
  ],
  "reasoning": "Brief explanation of merge strategy and reduction achieved"
}

If no merges are possible, return empty merges array."""

    user_prompt = f"""Tags to analyze:
{json.dumps(tag_names, indent=2)}

Identify which tags should be merged together."""

    try:
        # Log the request (DEBUG level for details)
        logger.debug("=" * 80)
        logger.debug("LLM REQUEST - Tag Auto-Merge")
        logger.debug(f"User ID: {current_user.id}")
        logger.debug(f"Number of tags: {len(tag_names)}")
        logger.debug(f"Model: {settings.LLM_MODEL}")
        logger.debug("-" * 80)
        logger.debug("SYSTEM PROMPT:")
        logger.debug(system_prompt)
        logger.debug("-" * 80)
        logger.debug("USER PROMPT:")
        logger.debug(user_prompt)
        logger.debug("=" * 80)

        response = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)

        # Log the response (DEBUG level for details)
        logger.debug("=" * 80)
        logger.debug("LLM RESPONSE - Tag Auto-Merge")
        logger.debug(f"User ID: {current_user.id}")
        logger.debug(f"Usage: {response.usage}")
        logger.debug("-" * 80)
        logger.debug("RAW RESPONSE:")
        logger.debug(response.choices[0].message.content)
        logger.debug("-" * 80)
        logger.debug("PARSED RESULT:")
        logger.debug(json.dumps(result, indent=2))
        logger.debug("=" * 80)

        merges = result.get("merges", [])

        if not merges:
            return {
                "message": "No similar tags found to merge",
                "merges_performed": 0,
                "tags_merged": [],
                "reasoning": result.get("reasoning", "No merges suggested"),
            }

        # Perform the merges
        tags_by_name = {tag.name: tag for tag in tags}
        merged_tags = []
        total_articles_updated = 0

        for merge_group in merges:
            target_name = merge_group.get("target")
            source_names = merge_group.get("sources", [])

            if not target_name or not source_names:
                continue

            # Normalize target tag name
            target_name = target_name.strip().lower()

            # Get or create target tag
            target_tag = tags_by_name.get(target_name)
            if not target_tag:
                # Create new tag if it doesn't exist
                logger.info(f"Creating new tag '{target_name}' as merge target")
                target_tag = Tag(name=target_name, user_id=current_user.id)
                db.add(target_tag)
                db.flush()  # Get the ID assigned by database
                tags_by_name[target_name] = target_tag

            for source_name in source_names:
                if source_name == target_name:
                    continue

                source_tag = tags_by_name.get(source_name)
                if not source_tag:
                    logger.warning(f"Source tag '{source_name}' not found, skipping")
                    continue

                # Find all articles with source tag
                # Use PostgreSQL JSON array contains operator @>
                from sqlalchemy import cast
                from sqlalchemy.dialects.postgresql import JSONB

                articles = (
                    db.query(Article)
                    .filter(
                        Article.user_id == current_user.id,
                        cast(Article.tags, JSONB).contains(cast([source_name], JSONB)),
                    )
                    .all()
                )

                # Replace source tag with target tag in all articles
                for article in articles:
                    if article.tags and source_name in article.tags:
                        # Remove source tag
                        article.tags = [t for t in article.tags if t != source_name]
                        # Add target tag if not already present
                        if target_name not in article.tags:
                            article.tags.append(target_name)

                total_articles_updated += len(articles)

                # Delete source tag
                db.delete(source_tag)
                merged_tags.append(f"{source_name} → {target_name}")
                logger.info(
                    f"Merged tag '{source_name}' into '{target_name}' ({len(articles)} articles)"
                )

        db.commit()

        return {
            "message": f"Auto-merge completed: {len(merged_tags)} tags merged",
            "merges_performed": len(merged_tags),
            "tags_merged": merged_tags,
            "articles_updated": total_articles_updated,
            "reasoning": result.get("reasoning", ""),
        }

    except Exception as e:
        logger.error(f"LLM auto-merge error: {str(e)}")
        logger.error(f"Full exception: {repr(e)}")
        raise HTTPException(status_code=500, detail=f"Auto-merge failed: {str(e)}")
