# Player Avatar Crops Design

## Goal

Use the provided two-by-four character image as the source for player avatars shown after the game starts.

## Avatar Mapping

The source image is ordered as:

- Top row: 柯南, 哆啦A梦, 蜡笔小新, 海绵宝宝
- Bottom row: 小猪佩奇, 猪猪侠, 懒羊羊, 奶龙

Each character is cropped into a separate local asset while preserving the white rounded card border and checkered background.

## UI Behavior

The frontend maps player names to local avatar files. Player cards render the avatar image above the seat/name and role/status text. If a name is not in the map, the frontend uses a default avatar fallback style without changing backend room creation or role assignment.

## Scope

This change affects only static assets, frontend rendering, CSS, and tests. It does not alter role logic, room serialization, player names, or game stage flow.

## Testing

Add frontend source tests that verify:

- All eight character names have avatar mappings.
- The expected avatar files exist.
- Player cards render an image element with alt text.
- CSS includes avatar image styling.
