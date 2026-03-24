# MCP Tools

## Tools

### case_create
Create a new missing-dog case.

Input:
- title
- last_seen_at
- last_seen_location
- species
- breed_guess
- sex
- spayed_neutered
- chip_status
- collar_status
- medical_notes
- owner_notes
- image_paths[]

Returns:
- case_id
- normalized_case_summary

### case_add_images
Attach more images and generate embeddings.

### case_get
Return a compact case summary.

### search_public_web
Search public indexed web results using case attributes and location.

Args:
- case_id
- radius_miles
- days_back
- page
- limit

### search_found_pet_sources
Run configured adapters against shelter/found-pet sources.

Args:
- case_id
- sources[]
- page
- limit

### search_browser_session
Use the user's own authenticated browser session if enabled.
Must refuse if browser-session mode is disabled.

### candidate_list
List candidate leads for a case.

### candidate_score
Return explainable component scores for one candidate.

### candidate_mark
Mark candidate as:
- likely_match
- false_positive
- repost
- follow_up
- uncertain

### crawl_run
Execute one full crawl pass.

### crawl_digest
Return summary of new leads since timestamp.

### case_export_bundle
Export markdown + json + screenshots manifest.

## Resources

### case://active
Active cases summary.

### case://{case_id}
Case detail snapshot.

### candidates://{case_id}
Ranked candidates for a case.

### report://daily/{yyyy-mm-dd}
Daily crawl report.
