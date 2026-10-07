# Contract bugs found in the blind-written SSE client

The frontend SSE client (`web-simulator/src/lib/api.ts`) was written from a
documented contract, never against a running server. Reading it against the
backend found three defects. Recorded here so they are not "fixed" in a way
that loses the reasoning.

## 1. `listTools()` calls a tool that does not exist

`api.ts:171-172`:

```ts
listTools: () => callTool('list_tools', {}),
```

`src/api/rest.py`'s TOOLS registry has no `list_tools` entry (verified: grep
count 0). Any call returns HTTP 404. DemoFlow.tsx calls this to show the tool
count before the chain runs, so the count silently never appears.

Tool discovery is an MCP protocol operation (`tools/list`), not a Sage tool.
It should call the MCP endpoint or be given a real REST route.

## 2. The parser drops `error` events

`api.ts:75-79` dispatches only `step` and `complete`. An `event: error` frame
is parsed, JSON-succeeds, matches neither branch, and is silently discarded.
So when the backend correctly emits an error frame, the frontend does
nothing — no error state, no message. The user sees the demo simply stop.

`handlers.onError` is only ever called for a network-level failure
(lines 52, 57, 62), never for an application-level error frame.

## 3. `AgenticComplete.steps` is typed as an array but receives a count

`api.ts:25-30`:

```ts
export interface AgenticComplete {
  status: string
  steps: AgenticStep[]      // <-- array
  synced_record_id?: string
  reason?: string
}
```

The documented backend contract sends `steps` as a NUMBER (how many steps
completed). A consumer written against this type will treat a number as an
array — `.length` yields undefined, `.map` throws.

This is a type-level lie that TypeScript cannot catch, because the value
arrives as untyped JSON at runtime.

## 4. RULED OUT — the parser does NOT drop the final frame

This was investigated and **disproved**. Recording it because the reasoning is
worth keeping and the wrong conclusion was nearly reported as fact.

The concern: `processBuffer` splits on `\n` and keeps the last element
(`buffer = lines.pop() || ''`). A well-formed SSE payload ends `\n\n`, so the
final split element is `''` and it gets popped — apparently losing the blank
line that should dispatch the last frame.

Traced through the real semantics (accumulate into buffer, pop the partial
line, dispatch on blank, final flush only `if (buffer.trim())`), a two-frame
payload parses correctly at every chunk size tested:

```
chunk=10000 -> [('step', ...), ('complete', {'status': 'success'})]
chunk=  500 -> [('step', ...), ('complete', {'status': 'success'})]
chunk=   37 -> [('step', ...), ('complete', {'status': 'success'})]
chunk=    7 -> [('step', ...), ('complete', {'status': 'success'})]
```

The final `\n\n` yields two trailing empties; `pop` removes one, and the
remaining one is processed as the dispatch trigger. The `buffer.trim()`
guard is not the problem because by then the frames have already dispatched.

The failure was in a Python *mirror* of this logic written to validate the
backend against it: that mirror reset its accumulated `event:`/`data:` state
per chunk, so a frame split across a boundary lost its data lines and parsed
as zero frames. The mirror was wrong, not the frontend.

**Lesson:** the reference implementation used to test a contract is itself
code that can be wrong. It now validates known-good and known-bad payloads
before being trusted, so it cannot silently manufacture a phantom bug.

## Why this matters more than a normal type bug

Every one of these produces a *silently wrong* result rather than an error:
the tool count never renders, the error state never appears, and a numeric
field is treated as a collection. A demo that half-works is worse than one
that visibly fails, because a judge cannot tell which parts are real.