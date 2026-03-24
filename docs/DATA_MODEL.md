# Data Model

## Case
- id
- title
- species
- breed_guess
- sex
- spayed_neutered
- chip_status
- collar_status
- medical_notes
- last_seen_at
- last_seen_lat
- last_seen_lng
- search_radius_miles
- status

## CaseImage
- id
- case_id
- path
- sha256
- embedding_whole
- embedding_crop
- embedding_head
- metadata_json

## Candidate
- id
- case_id
- source_name
- source_url
- external_id
- title
- snippet
- found_at
- lat
- lng
- location_text
- image_urls[]
- evidence_hash
- dedupe_group
- raw_json

## CandidateScore
- candidate_id
- text_score
- geo_score
- time_score
- attribute_score
- image_score
- repost_penalty
- final_score
- explanation_json

## ReviewAction
- id
- candidate_id
- action
- actor
- note
- created_at
