# Architecture

## Subsystems

### 1. Intake
Normalizes flyer OCR and manual input into a Case record.

### 2. Source adapters
Collect candidates from:
- public web search
- official shelter pages / APIs
- found-pet services
- optional browser-session searches explicitly enabled by the user

### 3. Vision
Creates embeddings for:
- whole image
- dog crop
- head crop
Calculates similarity against candidate images.

### 4. Ranking
Combines:
- text similarity
- image similarity
- geospatial proximity
- time overlap
- attribute agreement
- repost penalty
Outputs an explainable score bundle.

### 5. Evidence
Stores:
- raw source url
- retrieval time
- normalized extraction
- screenshot path
- hash for dedupe
- operator notes

### 6. MCP surface
Exposes stable tools and resources to Claude Code.

### 7. Operator console
Minimal local UI for case review and export.
