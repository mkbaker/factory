# Factory backlog

`/factory next` takes the first unchecked line, checks it off, and runs it through the loop.
When this list is empty it pulls the oldest open GitHub issue labelled `factory` instead.
Keep each item small enough to be one mergeable change.

A line can be plain text or a GitHub issue reference (`- [ ] #30`); issue jobs read the
issue and comments, and their PR closes the issue.

To hold a line until an issue's work is merged, say so in the line:
`- [ ] Tidy the log copy — depends on #74`.

`/factory next` checks lines off here but never commits this file, so parallel job PRs
don't conflict on it. Commit your backlog edits through a normal PR whenever you like.

<!-- Example:
- [ ] Show the count of failed jobs in the page header
-->
