# BMGD Workflows

## Available Workflows in bmgd

**brainstorm-game**
- Path: `.bmad/bmgd/workflows/1-preproduction/brainstorm-game/workflow.yaml`
- Facilitate game brainstorming sessions by orchestrating the CIS brainstorming workflow with game-specific context, guidance, and additional game design techniques.

**game-brief**
- Path: `.bmad/bmgd/workflows/1-preproduction/game-brief/workflow.yaml`
- Interactive game brief creation workflow that guides users through defining their game vision with multiple input sources and conversational collaboration

**gdd**
- Path: `.bmad/bmgd/workflows/2-design/gdd/workflow.yaml`
- Game Design Document workflow for all game project levels - from small prototypes to full AAA games. Generates comprehensive GDD with game mechanics, systems, progression, and implementation guidance.

**narrative**
- Path: `.bmad/bmgd/workflows/2-design/narrative/workflow.yaml`
- Narrative design workflow for story-driven games and applications. Creates comprehensive narrative documentation including story structure, character arcs, dialogue systems, and narrative implementation guidance.

**game-architecture**
- Path: `.bmad/bmgd/workflows/3-technical/game-architecture/workflow.yaml`
- Collaborative game architecture workflow for AI-agent consistency. Intelligent, adaptive conversation that produces a decision-focused game architecture document covering engine, systems, networking, and technical design optimized for game development.

**code-review**
- Path: `.bmad/bmgd/workflows/4-production/code-review/workflow.yaml`
- Perform a Senior Developer code review on a completed story flagged Ready for Review, leveraging story-context, epic tech-spec, repo docs, MCP servers for latest best-practices, and web search as fallback. Appends structured review notes to the story.

**correct-course**
- Path: `.bmad/bmgd/workflows/4-production/correct-course/workflow.yaml`
- Navigate significant changes during sprint execution by analyzing impact, proposing solutions, and routing for implementation

**create-story**
- Path: `.bmad/bmgd/workflows/4-production/create-story/workflow.yaml`
- Create the next user story markdown from epics/PRD and architecture, using a standard template and saving to the stories folder

**dev-story**
- Path: `.bmad/bmgd/workflows/4-production/dev-story/workflow.yaml`
- Execute a story by implementing tasks/subtasks, writing tests, validating, and updating the story file per acceptance criteria

**epic-tech-context**
- Path: `.bmad/bmgd/workflows/4-production/epic-tech-context/workflow.yaml`
- Generate a comprehensive Technical Specification from PRD and Architecture with acceptance criteria and traceability mapping

**retrospective**
- Path: `.bmad/bmgd/workflows/4-production/retrospective/workflow.yaml`
- Run after epic completion to review overall success, extract lessons learned, and explore if new information emerged that might impact the next epic

**sprint-planning**
- Path: `.bmad/bmgd/workflows/4-production/sprint-planning/workflow.yaml`
- Generate and manage the sprint status tracking file for Phase 4 implementation, extracting all epics and stories from epic files and tracking their status through the development lifecycle

**story-context**
- Path: `.bmad/bmgd/workflows/4-production/story-context/workflow.yaml`
- Assemble a dynamic Story Context XML by pulling latest documentation and existing code/library artifacts relevant to a drafted story

**story-done**
- Path: `.bmad/bmgd/workflows/4-production/story-done/workflow.yaml`
- Marks a story as done (DoD complete) and moves it from its current status → DONE in the status file. Advances the story queue. Simple status-update workflow with no searching required.

**story-ready**
- Path: `.bmad/bmgd/workflows/4-production/story-ready/workflow.yaml`
- Marks a drafted story as ready for development and moves it from TODO → IN PROGRESS in the status file. Simple status-update workflow with no searching required.


## Execution

When running any workflow:
1. LOAD {project-root}/bmad/core/tasks/workflow.xml
2. Pass the workflow path as 'workflow-config' parameter
3. Follow workflow.xml instructions EXACTLY
4. Save outputs after EACH section

## Modes
- Normal: Full interaction
- #yolo: Skip optional steps
