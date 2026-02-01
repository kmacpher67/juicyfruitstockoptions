---
description: Comprehensive checklist for creating implementation plans
---

When creating an implementation plan (`implementation_plan.md`), you MUST go through the following checklist, ensuring all aspects are considered before finalizing the plan.

## 1. Settings Updates
- [ ] Does this change require new environment variables?
- [ ] Are there changes to configuration files (e.g., config.py, .env)?
- [ ] Do default settings need to be updated?
- [ ] Impact on existing code (front and backend) inclusive of database collections/records? 


## 2. ACL Security Roles Compliance
- [ ] Does this feature introduce new users or roles?
- [ ] Are permissions properly checked for new endpoints/features?
- [ ] Does it adhere to the principle of least privilege?

## 3. Data Model ETL and Views
- [ ] Are there changes to the database schema?
- [ ] Does this affect existing ETL pipelines?
- [ ] Do we need simple views or complex aggregations?
- [ ] Is data migration required?

## 4. New Routes or Service/Models
- [ ] Are new API routes being added?
- [ ] Do new services follow the Single Responsibility Principle?
- [ ] Are models utilizing strong typing and validation?

## 5. Impact on AI Learning
- [ ] Does this change affect how the AI learns from the codebase?
- [ ] Are we providing enough context for future AI sessions?
- [ ] Is the code self-documenting for AI consumption?

## 6. Compliance with Mission Rules/Workflow
- [ ] Does this align with the core mission of the project? (Check `.agent/workflows/misson.md`)
- [ ] Are we following the defined workflow steps?

## 7. Compliance with Global Gemini.md Rules
- [ ] Review `~/.gemini/GEMINI.md` (or equivalent global rules).
- [ ] Adhere to all the rules inclusive of but not limited to: code style, logging, and testing standards defined there.

## 8. Best Practices from the Industry
- [ ] Are we using standard design patterns?
- [ ] Is the solution scalable and maintainable?
- [ ] Security best practices (OWASP, input validation)?

## 9. Fit into Epic-level Planning
- [ ] How does this relate to the current Epic? (Check `docs/Epic-level-planning.md`) 
- [ ] Does it block other work?
- [ ] Update and/or add sub items or comment on the exisitng items or sub-items. 
- [ ] Is it a prerequisite for future features or predicate?

## 10. Document.md Rules/Workflow Fit
- [ ] Follow the document rules (Check `.agent/rules/document.md`) 
- [ ] Review `docs/document.md` for documentation standards.
- [ ] Update `docs/` folders as appropriate.
- [ ] Ensure feature/requirement elaboration is memorialized.

## 11. Review Process
- [ ] Use `notify_user` to request review or proceed of Check `.agent/workflows/implementation_plan.md`.
- [ ] **PAUSE** work until feedback is received and the plan is approved.
- [ ] Iterate on the plan based on feedback. Only proceed to execution after explicit approval.

## 11. learning and new stuff
- [ ] Any questions or items not reviewed evaluated aka learned in the `docs/` folder for existing files or subsections should be updated or added per Check `.agent/workflows/learning-opportunity.md` workflow. 

