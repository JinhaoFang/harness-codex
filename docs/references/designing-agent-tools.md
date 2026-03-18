# Designing Agent Tools: Lessons from Building Claude Code

> Source: https://x.com/trq212/status/2027463795355095314
>
> Author: @trq212

One of the hardest parts of building an agent harness is constructing its action space.

Claude acts through Tool Calling, but there are a number of ways tools can be constructed in the Claude API with primitives like bash, skills and recently code execution.

Given all these options, how do you design the tools of your agent? Do you need just one tool like code execution or bash? What if you had 50 tools, one for each use case your agent might run into?

To put myself in the mind of the model I like to imagine being given a difficult math problem. What tools would you want in order to solve it? It would depend on your own skills!

- Paper would be the minimum, but you'd be limited by manual calculations.
- A calculator would be better, but you would need to know how to operate the more advanced options.
- The fastest and most powerful option would be a computer, but you would have to know how to use it to write and execute code.

This is a useful framework for designing your agent. You want to give it tools that are shaped to its own abilities. But how do you know what those abilities are? You pay attention, read its outputs, experiment. **You learn to see like an agent.**

Here are some lessons we've learned from paying attention to Claude while building Claude Code.

---

## Lesson 1: AskUserQuestion Tool

When building the `AskUserQuestion` tool, our goal was to improve Claude's ability to ask questions (often called elicitation).

While Claude could just ask questions in plain text, we found answering those questions felt like they took an unnecessary amount of time. How could we lower this friction and increase the bandwidth of communication between the user and Claude?

### Approach 1: ExitPlanTool Parameter

The first thing we tried was adding a parameter to the `ExitPlanTool` to have an array of questions alongside the plan. This was the easiest thing to implement, but it confused Claude because we were simultaneously asking for a plan and a set of questions about the plan.

- What if the user's answers conflicted with what the plan said?
- Would Claude need to call the `ExitPlanTool` twice?

We needed another approach.

### Approach 2: Modified Markdown Format

Next we tried modifying Claude's output instructions to serve a slightly modified markdown format that it could use to ask questions. For example, we could ask it to output a list of bullet point questions with alternatives in brackets. We could then parse and format that question as UI for the user.

While this was the most general change we could make and Claude even seemed to be okay at outputting this, it was not guaranteed. Claude would:

- Append extra sentences
- Omit options
- Use a different format altogether

### Approach 3: Dedicated Tool (Final Solution)

Finally, we landed on creating a tool that Claude could call at any point, but it was particularly prompted to do so during plan mode. When the tool triggered we would show a modal to display the questions and block the agent's loop until the user answered.

This tool allowed us to:

- Prompt Claude for a structured output
- Ensure that Claude gave the user multiple options
- Give users ways to compose this functionality (e.g., calling it in the Agent SDK or using it in skills)

**Most importantly, Claude seemed to like calling this tool and we found its outputs worked well.** Even the best designed tool doesn't work if Claude doesn't understand how to call it.

Is this the final form of elicitation in Claude Code? We're not sure. As you'll see in the next example, what works for one model may not be the best for another.

---

## Lesson 2: From TodoWrite to Task Tool

When we first launched Claude Code, we realized that the model needed a Todo list to keep it on track. Todos could be written at the start and checked off as the model did work. To do this we gave Claude the `TodoWrite` tool, which would write or update Todos and display them to the user.

But even then we often saw Claude forgetting what it had to do. To adapt, we inserted system reminders every 5 turns that reminded Claude of its goal.

### The Problem with TodoWrite

But as models improved, they not only did not need to be reminded of the Todo List but could find it limiting:

- Being sent reminders of the todo list made Claude think that it had to stick to the list instead of modifying it
- We also saw Opus 4.5 get much better at using subagents, but how could subagents coordinate on a shared Todo List?

### The Solution: Task Tool

Seeing this, we replaced `TodoWrite` with the Task Tool. Whereas Todos were about keeping the model on track, Tasks were more about helping agents communicate with each other. Tasks could:

- Include dependencies
- Share updates across subagents
- Be altered and deleted by the model

**Key Insight:** As model capabilities increase, the tools that your models once needed might now be constraining them. It's important to constantly revisit previous assumptions on what tools are needed. This is also why it's useful to stick to a small set of models to support that have a fairly similar capabilities profile.

---

## Lesson 3: Context Building with Search Tools

A particularly important set of tools for Claude are the search tools that can be used to build its own context.

### The RAG Approach

When Claude Code first came out, we used a RAG vector database to find context for Claude. While RAG was powerful and fast it:

- Required indexing and setup
- Could be fragile across a host of different environments
- **Most importantly:** Claude was given this context instead of finding the context itself

### The Grep Approach

But if Claude could search on the web, why not search your codebase? By giving Claude a Grep tool, we could let it search for files and build context itself.

**This is a pattern we've seen as Claude gets smarter, it becomes increasingly good at building its context if it's given the right tools.**

### Progressive Disclosure

When we introduced Agent Skills we formalized the idea of **progressive disclosure**, which allows agents to incrementally discover relevant context through exploration.

- Claude could read skill files
- Those files could then reference other files that the model could read recursively
- A common use of skills is to add more search capabilities to Claude like giving it instructions on how to use an API or query a database

Over the course of a year Claude went from not really being able to build its own context, to being able to do nested search across several layers of files to find the exact context it needed.

**Progressive disclosure is now a common technique we use to add new functionality without adding a tool.**

---

## Lesson 4: When Not to Add a Tool

Claude Code currently has ~20 tools, and we are constantly asking ourselves if we need all of them. **The bar to add a new tool is high, because this gives the model one more option to think about.**

For example, we noticed that Claude did not know enough about how to use Claude Code. If you asked it how to add a MCP or what a slash command did, it would not be able to reply.

### Option 1: System Prompt (Rejected)

We could have put all of this information in the system prompt, but given that users rarely asked about this, it would have:

- Added context rot
- Interfered with Claude Code's main job: writing code

### Option 2: Progressive Disclosure Link (Partial Success)

Instead, we tried a form of progressive disclosure. We gave Claude a link to its docs which it could then load to search for more information. This worked but we found that Claude would load a lot of results into context to find the right answer when really all you needed was the answer.

### Option 3: Claude Code Guide Subagent (Current Solution)

So we built the **Claude Code Guide subagent** which Claude is prompted to call when you ask about itself. The subagent has extensive instructions on:

- How to search docs well
- What to return

While this isn't perfect (Claude can still get confused when you ask it about how to set itself up), it is much better than it used to be! **We were able to add things to Claude's action space without adding a tool.**

---
