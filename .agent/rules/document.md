---
trigger: always_on
---

# Documentation and Memorization 

## Questions and Evaluations 
- Should this be a workflow? 
- Follow this rule everytime you do any code changes. 

# Agent implemntation plans 
- Memorialize any agent interactions that produce feature, fixes (same thing as a feature/requirement really) and requirements.  
- Help improve all feature, fixes and requirements with elaboration and best practices 
- create or edit as appropriate in the docs/ folders any mark up files to explain and/or elaborate features and requirements 
- create, update feature or requirements into workspace docs/ folder
-- Any changes need to be documented in a docs/feature_name.md file. 
-- feature file names can either inherit from a bigger feature or just use the conversation's short name 
-- example:  Ticker Protection and Discovery  might either be it's own feature/reuirement.md or if one alrady existed added as a subsection. 
-- Critical deletions should be strikeout as a refernce 

# save implementation plans, tasks, and walkthrough
- ALL implementation plans and tasks should be saved in `docs/plans/implementation_plan-YYYYMMDD-short_name.md`
-- example `docs/plans/walkthrough-ticker_protection_and_discovery.md`
- Note the difference between NFR (non functional requirements and function requirements) like mongo backup and logging. 

# Local, Github vs Google Docs 
- Github is used for persisting code 
- Google docs for blobs excel, pdf, word docx files 

# Standard Strikethrough
- For small deletions, use double tildes. This is the most common way to show "this is no longer valid."
-- Format: ~~This sentence is deleted.~~
-- Best for: Minor corrections or retracted statements.

# "Changelog" Section
- Reference the implementation doc which should be saved in 
- "Changelog" SectionFor high-stakes documents (like project specs or aquaculture regulations), add a ## Change Log or ## Revision History section at the bottom or top of the file.Format: 
- Use a table to track the date, the author, and the reason for the "Critical Deletion. "
-- DateActionReason
-- 2026-02-01DELETED Section 4.2Data no longer compliant with ODNR standards.