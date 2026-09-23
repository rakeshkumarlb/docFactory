---
app: kitchenhq
topic: data--profile
summary: 
updated: 2026-09-23
---

# Data  Profile

## Restrictions

- [F-0061] `user_profile.restrictions` is household-editable on the Profile page, and each entry is scoped `per_meal` or `week`. — src: store/kitchenhq/docs/repo/README.md

## Household members

- [F-0153] `household_members` holds individual household members (`id`, `name`, `dietary_preferences` JSON array, `health_conditions` JSON array). — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0154] `household_members` CRUD is REST-only (`/api/household-members`), edited by a human on the Profile page rather than through an agent tool, and the rows are embedded in `GET /api/dashboard` as `household_members`. — src: store/kitchenhq/docs/repo/CLAUDE.md

## User profile

- [F-0155] `user_profile.restrictions` is a JSON list of `{id, label, category, enabled, scope, value?}` where `scope` is `"per_meal"` or `"week"`. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0156] `user_profile` holds the booleans `allow_recipe_invention` and `allow_unapproved_recipes`; the latter is captured but unused until a recipe-approval workflow exists. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0157] `user_profile.skip_meals` is JSON `{day_of_week: [meal_type, ...]}` listing slots to leave unplanned for the coming week. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0158] `user_profile.preferred_tags` and `excluded_tags` are JSON string arrays drawn from the categorized taxonomy in `shared/tags.py` (cuisine / dietary / allergen / religious / method), a suggested vocabulary rather than an enforced enum. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0159] `shared/tags.py` is vendored the same way as `shared/constants.py` and exposed to chatui via `GET /api/dashboard`'s `constants.tags`. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0160] `user_profile.favorite_recipes` is a legacy JSON field (max 10, newest first) that nothing currently writes to, since the star-rating flow that populated it was removed in favour of `household_members`. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0161] Example restrictions: `no_nonveg_lunch` (`per_meal`; the old egg/meat/fish rule) and `lunch_variety` (`week` scope with a `value` parameter, its minimum distinct count; the old five-distinct-lunches rule). — src: store/kitchenhq/docs/repo/CLAUDE.md

## Household preferences tool

- [F-0162] The `get_household_preferences` MCP tool folds household members, restrictions, tags, skip meals, the free-text chef note (`user_profile.notes`) and `favorite_recipes` together, plus a `has_preferences` bool and a `guidance` line. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0163] `get_household_preferences` is the single shared source of household rules, preferences, conditions and restrictions: the Executive Chef and Sous Chef prompts tell them to consult it before deciding what to cook, and the Food Inspector consults the same tool when auditing, never a duplicated rules file. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0164] Household preferences are optional context: when `get_household_preferences` comes back empty (`has_preferences: false`, as on a fresh install) every role proceeds anyway. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0165] `restrictions` is excluded from the empty-preferences check because it always carries its two seeded defaults. — src: store/kitchenhq/docs/repo/CLAUDE.md
