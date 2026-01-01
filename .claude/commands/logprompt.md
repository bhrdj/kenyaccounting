---
allowed-tools: Read, Edit, Write, Glob
argument-hint: [title] <prompt text or "last" for previous prompt>
description: Append a prompt to PromptHistory.md in the current repo
---

# /logprompt Command

Append a prompt entry to the PromptHistory.md file in the current directory (typically `specs/PromptHistory.md`).

## Instructions

1. First, locate the PromptHistory.md file in the current repo. Check these locations in order:
   - `specs/PromptHistory.md`
   - `PromptHistory.md`
   - If not found, create `specs/PromptHistory.md`

2. Read the existing file to understand the format. The standard format is:
   ```markdown
   ## [Section Name]

   ### [Prompt Title]
   [prompt text here]
   ```

3. Parse the arguments:
   - If `$ARGUMENTS` is empty or just "last", use the user's previous prompt from the conversation
   - Otherwise, the first argument is the title, and remaining text is the prompt content

4. Append the new prompt entry at the end of the file, following the existing format:
   - If this is a continuation of an existing section (like "Claude Code - Project Task Planning"), just add a new `###` subsection
   - If it's a new topic, create a new `##` section first

5. Confirm the addition to the user with a brief summary.

## Arguments

$ARGUMENTS
