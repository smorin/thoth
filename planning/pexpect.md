Thanks! I’ll prepare a comprehensive deep dive on using `pexpect` to test your `thoth` interactive CLI program built with Prompt Toolkit. This will include a general-purpose test framework with examples, detailed tutorials on simulating user interactions (including arrow keys and tab completion), and guidance on structuring your `thoth_test` script to orchestrate and report results from multiple scenarios.


# Testing an Interactive CLI with Pexpect – Approaches and Best Practices

## Overview: Challenges of Testing Interactive CLI Tools

Testing an interactive command-line application (especially one built with libraries like **prompt\_toolkit**) is more complex than testing a typical batch CLI command. Unlike one-off commands (where you can simply run a subprocess with some input and capture output), interactive CLIs maintain a live session, respond to **key presses** (arrow keys, Tab, etc.), and often require a real terminal (TTY) to function correctly.

In the case of *Thoth* – a Python CLI using Prompt Toolkit – the current test harness (`thoth_test`) uses a black-box approach: it runs the `thoth` executable with given arguments using `subprocess.Popen`, then checks the exit code and output text. This works for testing *non-interactive “quick mode”* commands (where you pass a query and get output immediately). However, it doesn’t cover *interactive mode* where the program expects a user at a terminal, typing commands and navigating with the keyboard. Simply piping input via `stdin` is **not sufficient** for such cases – Prompt Toolkit bypasses the normal stdin/stdout buffering and directly manipulates the terminal for features like autocompletion menus, cursor movement, and so on. In fact, by default Prompt Toolkit reads from an actual TTY device and renders output with complex ANSI control codes. Without a proper pseudo-terminal, the interactive app might hang or not behave normally.

**Key challenge:** *Simulating real user interactions (keystrokes, live input) in tests.* We need an approach that makes the CLI think it’s talking to a real user in a terminal. This involves handling things like waiting for prompts, sending special keys (e.g. Up arrow for history, Tab for completion), and capturing the dynamic output.

## Approach 1: Naïve Method (Direct Stdinput/Piping) – Why It Falls Short

One tempting approach is to feed input to the program’s standard input (e.g. using `Popen.communicate()` or piping a script of keystrokes). For a simple program that reads line-by-line from stdin, that might work. But for a Prompt Toolkit-based interactive app, this **naïve approach doesn’t work correctly**:

* **No TTY/Terminal Emulation:** Prompt Toolkit’s rich interaction (keyboard shortcuts, autocompletion popup, etc.) relies on a terminal environment (cursor positioning, ANSI escape sequences, etc.). If you just pipe input from stdin without a TTY, the application may not initialize properly or may behave differently. As the Prompt Toolkit docs note, its rendering engine is built for a real interactive layout. In unit tests, developers replace the real input/output with dummy ones for control – which implies that a direct stdin/stdout feed won’t mimic a user session well.

* **Inability to Send Special Keys:** A pipe can easily send ordinary characters and newlines, but how do you send an “Up Arrow” or “Tab” through a pipe? These aren’t simple characters – they’re interpreted by the terminal and applications as **escape sequences**. Without a proper terminal, sending `\x1b[A` (the ESC sequence for Up arrow) to stdin might not have the intended effect, because the app might not be listening in raw mode or at all.

* **No Real-Time Interaction:** Piping input all at once doesn’t allow the test to **react** to output. In interactive sessions, the program might output a prompt or message and then wait for user input. A robust test needs to wait for that prompt before sending the next input. Standard piping or `communicate()` doesn’t easily allow this stepwise synchronization.

Given these issues, the Thoth test suite in its current form **skips interactive behavior** – for example, there’s no test that launches `thoth` with no arguments to check the interactive REPL features. The “Ctrl-C graceful shutdown” test is marked to skip because sending an actual Ctrl-C is non-trivial with the basic subprocess method. Clearly, a more advanced technique is needed for interactive testing.

## Approach 2: Using Pexpect with a Pseudoterminal (Recommended)

**Pexpect** is a Python module designed exactly for this kind of situation. It allows you to spawn a child process **with a pseudo-terminal**, send inputs to it, and watch for expected outputs. In essence, *Pexpect lets your test script behave like an automated human typing commands*. The child process (your CLI app) cannot tell it’s not a real user – it sees a TTY device and receives keystrokes, including special keys, just as if someone were at a terminal.

Key benefits of using Pexpect for Thoth’s interactive tests:

* **True Terminal Emulation:** Pexpect spawns the process in a PTY, so libraries like Prompt Toolkit will detect a terminal. This means features like fancy rendering, autocompletion, and key bindings remain enabled. From the app’s perspective, there is a real user terminal.

* **Step-by-Step Interaction:** You can script the dialogue: wait for the program to output specific text (like a prompt or question) and then respond with simulated key presses. This is done via an `.expect()` and `.send()` loop: the test waits for an expected pattern in the child’s output, then sends a reply. For example: `child.expect('Name:')` then `child.sendline('anonymous')`. This granular control is essential for syncing with the app’s state.

* **Sending Special Keystrokes:** With Pexpect, you’re not limited to normal characters. You can send raw byte sequences or even use helpful mappings. For instance, the ANSI escape sequence for the **Down Arrow** key is `\x1b[B`. Pexpect can send that just like any other string, and the application will interpret it as a down-arrow key press. (Similarly, Up Arrow is `\x1b[A`, Left is `\x1b[D`, Right is `\x1b[C]`, and Tab is `\t` or `\x09`.) In fact, since your program already uses Prompt Toolkit, you can leverage its key definitions: Prompt Toolkit’s internal mapping `Keys.Up` corresponds to `'\x1b[A'` as well, so either using the raw escape or Prompt Toolkit’s `REVERSE_ANSI_SEQUENCES` mapping yields the same code.

* **Full Output Capture:** Pexpect captures **everything** the program writes to its stdout/stderr, including prompts, menus, etc. This allows your test to assert that expected text appeared (e.g. a help message or completion suggestion). Be mindful that Prompt Toolkit may output control characters (for cursor movement, color, etc.), but you can filter or regex-match the meaningful parts of the output.

**Recommendation:** For testing Thoth’s interactive mode, **Pexpect is the superior approach**. It was built for automating interactive applications, whereas the standard subprocess method cannot handle interactive flows. Next, we’ll dive into how to use Pexpect effectively and how to structure these tests.

## Pexpect Overview and Setup

Using Pexpect in Python is straightforward. First, install it (if not already in your testing environment) with `pip install pexpect`. Then, in your test script, you typically do the following:

1. **Spawn the CLI Process:** Use `pexpect.spawn` to start the `thoth` program. You can give the path to the executable and any arguments. For interactive mode, you might just do `pexpect.spawn('./thoth', encoding='utf-8', timeout=5)`. It’s often useful to set `encoding='utf-8'` so you get Python strings instead of bytes, and set a `timeout` (in seconds) for `.expect()` so tests don’t hang forever if something goes wrong. By default, `spawn` will allocate a pseudoterminal for the process, so no extra work is needed to create a TTY – Pexpect handles it.

2. **Expect an Initial Prompt or Output:** Once the process starts, your test should wait for some known text that indicates the program is ready for input. For example, Thoth might print a welcome message or a prompt like `Thoth> ` when in interactive mode. You can do `child.expect('Thoth>')` or whatever prompt string or regex reliably signifies readiness. (Using a regex pattern can be handy if the prompt may include ANSI color codes or dynamic content.)

3. **Send Input (Commands or Keystrokes):** Use `child.sendline(<text>)` to send a line of input (it appends an Enter key for you), or `child.send(<text>)` to send text without appending a newline. For instance, to simulate a user typing the command `help` and pressing Enter, you do `child.sendline('help')`. For special keys that are not “enter-terminated”, use `child.send()`: e.g. `child.send('\x1b[A')` to send an Up Arrow without a newline. (We’ll cover more on special keys in the next section.)

4. **Expect the Result:** After each input, wait for the application’s response using `child.expect()`. This could be a piece of text in the output, or even the next prompt appearing. For example, after sending `help\n`, you might expect to see usage text or a help menu that contains the word “Usage:”. You can do `child.expect('Usage:')`. If the output is long or multi-line, you might use regex or a few key snippets to ensure the important parts are present. You can also use `expect_exact` for exact matches, but usually a regex is more flexible (e.g., `child.expect(r'Usage:')` will find “Usage:” literally).

5. **Repeat Interactions as Needed:** If your scenario involves multiple back-and-forth steps (e.g., testing history navigation or autocompletion menus), continue the cycle: send the next key or command, then expect the resulting state or output. Pexpect allows you to build a full script of the conversation. You may also incorporate small delays if needed (though generally Prompt Toolkit apps process input synchronously, so waiting for the expected text is usually enough).

6. **End the Session Cleanly:** Finally, you may need to exit the interactive session. This could be done by sending a command like `exit` or pressing Ctrl+D/Ctrl+C depending on how your CLI is designed to quit. For example, if `exit` command causes Thoth to quit, do `child.sendline('exit')` and then `child.expect(pexpect.EOF)` to wait for the end-of-file, indicating the process exited. If Ctrl+C is a way to interrupt, you can send it via `child.send('\x03')` (`\x03` is the ETX character for Ctrl+C) or use Prompt Toolkit’s mapping (`REVERSE_ANSI_SEQUENCES[Keys.ControlC]` as shown in Pexpect examples). Ensure the process has indeed terminated (you might check `child.wait()` or rely on EOF as above).

Here’s a simple example that ties this together for an imaginary Thoth interactive session:

```python
import pexpect

# 1. Spawn the interactive Thoth CLI
child = pexpect.spawn('./thoth', encoding='utf-8', timeout=5)

# 2. Wait for the prompt (assuming the prompt contains "Thoth> ")
child.expect('Thoth> ')

# 3. Send a command at the prompt, e.g., "help"
child.sendline('help')

# 4. Expect some output from the help command (e.g., the usage line)
child.expect('Usage:')

# (Optional) simulate pressing the Up arrow to recall the last command
child.send('\x1b[A')  # Up arrow key
# After sending Up, the CLI might reprint the previous command (e.g., 'help').
# We can expect that 'help' appears again at the prompt line.
child.expect('help')

# (Optional) simulate Tab for autocompletion (depends on CLI's features)
child.send('\t')  # press Tab to trigger completion suggestions
# We might expect a list of suggestions or a completed text. For example:
child.expect('help        exit        list')  # (Just an example of possible suggestions)

# 5. Exit the interactive session
child.sendline('exit')
child.expect(pexpect.EOF)  # Wait for the program to terminate
```

In the above example, we used a made-up completion menu text for illustration – you would adjust the `expect()` patterns to what Thoth actually shows (perhaps a list of available commands, etc.). The flow demonstrates how to intermix sending normal commands (`sendline('help')`) with special keys (`send('\x1b[A')` for Up, `send('\t')` for Tab) and verify the program’s reactions at each step.

## Simulating Special Key Presses (Arrow Keys, Tab, etc.)

A big part of interactive testing is ensuring that **keyboard navigation and shortcuts** work as intended – for example, pressing the Up arrow should bring up the last command (history), Tab should auto-complete or suggest, arrow keys might navigate a menu or move the cursor. With Pexpect, simulating these keys is just about sending the right byte sequences:

* **Enter** – When using `sendline()`, Pexpect automatically appends the newline/Enter key. If needed explicitly, the Enter key is `'\r'` (carriage return) or `'\n'` (newline) – most terminals interpret both as Enter. (Pexpect uses `\r` by default for `sendline`.)

* **Arrow Keys** – As noted, the arrow keys correspond to ANSI escape sequences. Up = `\x1b[A`, Down = `\x1b[B`, Right = `\x1b[C`, Left = `\x1b[D`. These sequences start with the ESC character (`\x1b` which is `^[` in caret notation) followed by `[` and a letter. You can send them via `child.send()`. For example, to simulate five Down-arrow presses: `child.send('\x1b[B' * 5)` would send the code 5 times.

* **Tab** – The Tab key is ASCII 9, so you can send `'\t'` or `'\x09'`. Prompt Toolkit typically uses Tab to trigger autocompletion. After sending a Tab, your CLI might print a list of suggestions or complete the current word. Your test should then expect whatever indicator of completion occurs (perhaps part of the word being filled in, or a list of options printed above the prompt).

* **Ctrl-C / Ctrl-D** – These are common control keys. Ctrl-C (interrupt) is ASCII 3 (`\x03`), and Ctrl-D (EOF in terminal) is ASCII 4 (`\x04`). You can send those if you need to test how the program handles interrupts or EOF. For instance, to simulate a user pressing Ctrl-C to cancel an operation, do `child.send('\x03')`. With Prompt Toolkit, sending Ctrl-C might raise a KeyboardInterrupt inside your app – your test can then expect the app’s graceful shutdown message or prompt return. *(Be cautious: sending Ctrl-C will terminate the child process unless the app specifically catches it. In Thoth’s case, it might catch it to do a graceful checkpoint save.)*

* **Special keys via Prompt Toolkit mapping (optional):** If you prefer not to hard-code `\x1b[A` etc., you can use Prompt Toolkit’s key definitions. Since Thoth uses Prompt Toolkit, you could import `prompt_toolkit.keys.Keys` and `prompt_toolkit.input.ansi_escape_sequences.REVERSE_ANSI_SEQUENCES` in your test. For example: `from prompt_toolkit.keys import Keys; from prompt_toolkit.input.ansi_escape_sequences import REVERSE_ANSI_SEQUENCES; child.send(REVERSE_ANSI_SEQUENCES[Keys.Tab])`. This yields the correct sequence for Tab. This approach can make the test more self-documenting (using names like Keys.Up, Keys.Tab). However, it does add a dependency on prompt\_toolkit in the test environment, which you may or may not want. Sending the raw escape strings works fine as well.

When writing expectations around special key behavior, consider what output (if any) the CLI produces:

* **History (Up/Down):** Often, pressing Up doesn’t produce new output; it just edits the current prompt line (showing the previous command). However, from the perspective of the PTY, the characters of the previous command will be written to the output (the terminal line is updated). Pexpect can capture this. For example, if the last command was `"help"`, pressing Up might cause the characters `h`, `e`, `l`, `p` to appear (possibly with some backspaces/clears before them). A simple way to assert this is to expect the old command string to reappear. In our example above, after `child.send('\x1b[A')`, we did `child.expect('help')` to ensure the text *help* showed up again at the prompt.

* **Autocompletion (Tab):** Depending on implementation, Tab might immediately complete the text (in which case the partially typed command on the prompt suddenly becomes the full command), or it might open a dropdown/tooltip or list possible completions. In either case, your test should look for a known outcome. For instance, if the user typed `"st"` and pressed Tab, and Thoth auto-completes to `"status"`, then the prompt line now contains the word "status". Pexpect might not give you an easy hook to *just* the input line content, but since the terminal is being redrawn, you might see the letters `t`, `a`, `t`, `u`, `s` appear in sequence. A more reliable approach is if the app prints suggestions (like how shells show a list when multiple completions exist). If Thoth does that, you can expect one of the suggestion words to appear in the output. For example, if at an empty prompt Tab lists commands, you might do `child.expect('available commands')` or some snippet from the menu.

* **Navigating Menus/Lists:** If your CLI has multi-line selection lists (for example, Prompt Toolkit can create a scrollable selection using arrow keys), testing that can be tricky but doable. Each arrow key press likely highlights a different item and reprints the menu. Your test could send a Down arrow and then expect the *new item* to be highlighted (which might be indicated by a `>` pointer or inverse video text). This requires knowing how the UI indicates the selection. As an example, if the menu looks like:

  ```
  > Option A
    Option B
    Option C
  ```

  pressing Down might result in:

  ```
    Option A
  > Option B
    Option C
  ```

  You could verify that by expecting the `>` character to move from "Option A" line to "Option B" line, or simply expect the text of Option B to appear with the marker. (Keep in mind color codes may be present around the `>` or the option text, which you might need to accommodate in your pattern, e.g. using a regex like `r'> Option B'` which should match even if there are color codes, as long as they don’t break the order of characters.)

In summary, Pexpect gives you the power to **simulate any key press** and observe the effect. Leverage this to fully test interactive features: history recall, tab completion, canceling actions, navigation, etc. All of these are critical to ensure a good user experience, and now you can verify them in an automated way.

## Integrating Pexpect Tests into the Thoth Testing Framework

With the basics of Pexpect covered, the next consideration is how to organize these tests within your existing `thoth_test` framework. Since `thoth_test` was originally designed for one-shot commands, you’ll need to extend it (or create a new section in it) to handle interactive scenario tests. Here are some suggestions:

* **Separate Test Cases or Functions:** It may be simplest to write dedicated functions or test case entries for interactive sessions. For example, you could create a function `run_interactive_test_scenario(name, scenario_steps)` where `scenario_steps` is a sequence of expect/send actions. Each scenario can correspond to a particular feature (e.g., **TestInteractiveHistory**, **TestInteractiveCompletion**). This keeps the interactive logic distinct from the existing `TestCase` dataclass, which isn’t built to script multiple exchanges.

* **Define Scenarios Clearly:** For readability, you might define the scenario steps as a list of tuples, e.g.:

  ```python
  scenario = [
      # (expected_output_pattern, input_to_send)
      ("Thoth> ", "help\n"),           # expect prompt, then type help
      ("Usage:", None),                # expect usage in output (no new input yet)
      (None, "\x1b[A"),                # press Up (no specific output expected immediately, so pattern None)
      ("help", None),                  # after Up, expect the previous command to appear
      (None, "exit\n"),                # send exit to quit
  ]
  ```

  Then your test runner can iterate through this: for each step, if there’s a pattern, do an `expect`, if there’s input, do a `send` (or `sendline` if it includes `\n`). This approach makes it clear what the dialog is. You can also include delays or custom checks if needed (for example, after sending exit, expect EOF).

* **Use Timeouts and Error Handling:** Interactive tests can be more fragile if something goes wrong (e.g., if the CLI gets stuck on a prompt and our `expect` pattern never appears). Make sure to use reasonable timeouts in `expect()` (you can set a global timeout on the spawn, as we did with `timeout=5`, and/or specify per-expect). If an `.expect()` times out, Pexpect will raise an exception – you can catch that to provide a nicer error message or to ensure the child process is cleaned up. In a testing context, a timeout likely means a test failure (the expected output didn’t show up in time).

* **Capture Output for Debugging:** When a Pexpect test fails, it can be tricky to see what went wrong. One tip is to set `child.logfile = sys.stdout` (or to a file) to echo the child process’s output in real time. This way, if you run `thoth_test` in verbose mode, you’d see the interaction play out, which helps pinpoint where the expectations mismatched. You might enable this logging conditionally (e.g., only if a verbose flag is set in your test script) to avoid cluttering normal test output.

* **Reset State Between Runs:** Each interactive test should start the CLI fresh. Avoid reusing the same spawned process for multiple scenarios – spawn a new `./thoth` each time so that history and state don’t bleed over, and so if one test crashes the process, it doesn’t affect others. Also ensure any temporary files or configs created by an interactive session are cleaned (similar to how you already clean up files in TestCase with `cleanup_files`).

* **Consider Non-TTY Mode for Output Checking (if feasible):** One way to simplify output matching is to minimize ANSI color codes. Since Thoth uses `rich` and Prompt Toolkit, a lot of formatting could be present. You might consider running the CLI in a "dumb terminal" mode for tests. For example, you could set `TERM=dumb` in the environment or disable color output if the application supports an option or env var for that (some CLIs have `--no-color`). However, forcing a dumb terminal might disable some interactive features. An alternative is to strip ANSI escape codes from captured output before matching. You can do this by post-processing `child.before` or `child.after` strings with a regex like `re.sub(r'\x1b\\[[0-9;]*[A-Za-z]', '', text)` to remove ANSI sequences. That way, your expected patterns can be just the raw text. This is not always necessary, but it’s a good trick if color codes are making pattern matching hard.

* **Follow Prompt Toolkit Testing Guidance (if applicable):** Prompt Toolkit’s documentation suggests not asserting on low-level output bytes, but rather on the outcome/state. In our black-box approach, we don’t have direct access to internal state, so we rely on output text. To make tests less brittle, assert on high-level behaviors or messages, not on exact formatting. For example, checking that *“Research completed”* appears (regardless of color or surrounding whitespace) is better than expecting an exact full line match. Use regex patterns that capture the essence of the output and ignore incidental differences. This principle will make your interactive tests resilient to minor UI changes (like a tweak in formatting or color).

## Example Scenario: Testing Autocompletion in Thoth

Let’s walk through a concrete example of a test scenario using Pexpect – **simulating a user using Tab completion** in Thoth’s interactive mode:

* **Goal:** Verify that when the user types a partial command and presses **Tab**, the CLI suggests or completes the command.

* **Setup:** Assume Thoth has a set of commands (like `help`, `exit`, `list`, etc.). We expect that typing `he` + Tab will complete it to `help`.

**Steps:**

1. **Launch Thoth in interactive mode:** `child = pexpect.spawn('./thoth', encoding='utf-8', timeout=5)`.

2. **Wait for prompt:** `child.expect('Thoth> ')`. (We assume the prompt includes "Thoth> ". If not, adjust to whatever prompt or initial output exists.)

3. **Type `he` (no Enter yet):** `child.send('he')`. The user has started typing a command. No output is expected yet (the characters might appear on the terminal, but often echoing is handled internally by the library). We can optionally expect that `h` and `e` appear, but that might be too low-level. It might be safe to skip expecting anything here and go straight to the next action.

4. **Press Tab:** `child.send('\t')`. This should trigger the autocompletion. Now, what do we expect? If there is a unique match (`help`), Prompt Toolkit might automatically complete the text to "help ". If there are multiple matches, it might show a list. Let’s assume unique match for now.

5. **Expect completion:** We anticipate that after pressing Tab, the prompt line now has "help". Perhaps the application also echoes a space or just completes in-place. We can do `child.expect('help')` – but be careful: the letters "he" were already there, so strictly seeing "help" means we need the "lp" to appear. In practice, after Tab, the terminal may briefly show the completed text. Since we are capturing all output, we likely will see "lp" appear (or the whole "help" again if it refreshes the line). To keep it simple, `child.expect(r'help')` will succeed as soon as the sequence "help" appears anywhere in the output (which should happen when the line is rendered with the completed word).

6. **Press Enter to execute the completed command:** `child.sendline('')` (since "help" is now typed out, just sending an empty `sendline` will send the Enter key). Alternatively, we could have included the Enter in the Tab if we knew it auto-completes and immediately executes – but usually Tab doesn’t execute, it just completes, so an explicit Enter is needed to run the command.

7. **Expect help output:** Now the help command actually runs. We expect the usage text or help menu. For instance, `child.expect('Usage:')` and maybe `child.expect('Quick usage:')`, etc., to verify the help text content (these are patterns used in the non-interactive help test as well).

8. **Exit:** After confirming the help output, we should exit the session (unless the help command already causes an exit, but likely not). We send, say, `child.sendline('exit')` and then expect EOF: `child.expect(pexpect.EOF)`.

This scenario would confirm that Tab completion works and yields the correct command. If Thoth’s completion instead shows a list (say the user typed `h` and pressed Tab, maybe multiple commands start with `h`), then step 5 would change: we’d expect a list of suggestions, e.g., `child.expect('help')` and `child.expect('history')` if those were in the list of suggestions.

**Common failing points** to watch out for in this scenario:

* If the pattern in `expect` is too specific (e.g., expecting the exact prompt string including colors), the test might fail even though the feature worked. Prefer key substrings (like `'Usage:'` which is definitely in the help text) over full lines with formatting.
* Timing issues: If the Tab completion is fast, the `expect('help')` might match the partial "he" that was already there. To avoid false positives, you could use an anchor or context in the regex. For example, if the prompt resets to a new line, you might expect something like `\r\nThoth> help` (meaning a carriage return, new prompt, and then "help" at the prompt). This can get complex. Another strategy is to perform `expect` in sequence: expect the prompt to reappear or the help output to start, which indirectly confirms the completion happened.
* The `child.send('he')` could potentially be sent too quickly before the prompt is ready (though our flow waited for the prompt in step 2). Always ensure you `expect` the prompt *before* sending input at a fresh prompt.

By carefully designing the expect/send sequence and using a bit of regex, you can reliably test even these interactive niceties.

## Pitfalls and Best Practices for Pexpect Tests

To wrap up, here are some **best practices** and things to consider when using Pexpect for your test suite:

* **Use Regex for Flexible Matching:** Outputs in interactive programs can include dynamic data (timestamps, IDs, etc.) or ANSI codes. Write expected patterns with regex wildcards (e.g., `r'\d{4}-\d{2}-\d{2}'` to match a date in output) instead of hard-coding exact strings. This is already done in Thoth’s existing tests and should be carried over to interactive expectations.

* **Beware of ANSI Escape Characters:** Terminal applications often use escape sequences for color and cursor movement. These may appear in the captured output as weird characters (e.g., `\x1b[?7l`). If you don’t account for them, an `.expect('SomeText')` might fail because the text is interwoven with escape codes. You can strip them out or use a pattern that ignores them. For example, insert `\x1b\[[0-9;]*[A-Za-z]` patterns in your regex to consume any ANSI codes in between expected words. If this becomes too cumbersome, consider turning off color in the app during tests as mentioned earlier.

* **Leverage Timeouts but Tune Them:** Pexpect’s default timeout is 30 seconds, which is usually fine. If your CLI might sometimes take longer (e.g., calling external API?), you can adjust per test. In `thoth_test`, `TEST_TIMEOUT` is set to 30, but for interactive steps, you might not need that long if you know each step should respond quickly. Using a shorter timeout for each expect (like 5 seconds as in our examples) can make tests fail faster when something is wrong, rather than hanging. However, be careful not to set it too low and get false failures on slower systems. You could also implement a global timeout for the whole scenario if needed.

* **Clean Up Child Processes:** If a test fails in the middle (say an unexpected output causes an `.expect()` timeout), the spawned process might still be running (stuck waiting for input). Make sure to kill or close it. A try/finally in your test can do:

  ```python
  child = pexpect.spawn(...)
  try:
      # interactions...
  finally:
      child.close(force=True)
  ```

  This ensures no stray `thoth` processes linger if a test aborts. In practice, when the Python process exits, child should terminate, but it’s good to be explicit.

* **Document the Scenarios:** Since interactive tests can be complex, include comments or use descriptive test names for each scenario. For instance, in the test output, seeing a test labeled "Interactive History Recall works" is much clearer than something generic. Your `thoth_test` script could group interactive tests together and label them accordingly when printing results (perhaps by giving them a different test\_id prefix like “INT-01”, “INT-02”, etc., to distinguish from the existing batch tests).

* **Manual Verification:** When writing a new interactive test, it helps to manually try those key presses in the real program to see what the output looks like. That way you know what to expect. You can even copy some of the output to use in your expected patterns, adjusting for regex needs. This reduces guesswork.

* **Gradual Build-Up:** Add one interactive test at a time and get it passing reliably before adding more. Interactive tests have a tendency to be flaky if not done carefully (due to timing or environment differences). By iterating slowly, you can ensure stability. Once stable, these tests will give great confidence that the interactive aspects of Thoth work across updates.

## Conclusion and Recommendation

After exploring both approaches, the **clear recommendation is to use Pexpect for testing Thoth’s interactive CLI features**. The subprocess-based method (sending input via stdin without a TTY) is insufficient for Prompt Toolkit applications – it cannot simulate real user key interactions and will miss covering important UI behavior. Pexpect, on the other hand, provides a robust framework to **mimic a user session**: it opens a pseudoterminal, sends keystrokes, and verifies the CLI’s responses as if a person were at the keyboard. We’ve outlined how to use Pexpect, including handling special keys like arrows and Tab, and given examples of structuring test scenarios. This approach aligns with good testing practice for interactive programs, treating them as black-box systems while still exercising complex input/output sequences.

In terms of architecture, the best setup is to integrate Pexpect-driven tests into your existing `thoth_test` suite in a maintainable way – e.g., separate scenario definitions, clear expected patterns, and using the same pass/fail reporting mechanism (so that interactive tests show up in the summary alongside existing tests). By doing so, you’ll extend the coverage of your test suite to the interactive mode without sacrificing clarity or reliability.

In summary, **use Pexpect to simulate real terminal interactions** for Thoth: it will enable comprehensive testing of features like autocompletion, history, keyboard shortcuts, and graceful interrupts. This ensures that your CLI behaves correctly not just in scripted one-shot calls, but also in the hands of an interactive user – and you’ll have automated tests to prove it. Happy testing!

**Sources:**

* Pexpect documentation and usage examples
* Stack Overflow – sending arrow keys via Pexpect
* Prompt Toolkit documentation – unit testing considerations
* Thoth test suite (`thoth_test`) implementation (for context on current testing approach and expected outputs)


GitHub
thoth_test

https://github.com/smorin/thoth/blob/f3aacc45c9b8a6a9451d5b4431f8da11e24124f2/thoth_test#L8-L15
GitHub
thoth_test

https://github.com/smorin/thoth/blob/f3aacc45c9b8a6a9451d5b4431f8da11e24124f2/thoth_test#L126-L134

Unit testing — prompt_toolkit 3.0.38 documentation

https://python-prompt-toolkit.readthedocs.io/en/3.0.38/pages/advanced_topics/unit_testing.html

How to make prompt-toolkit work on dumb terminals #1032 - GitHub

https://github.com/prompt-toolkit/python-prompt-toolkit/issues/1032
GitHub
thoth_test

https://github.com/smorin/thoth/blob/f3aacc45c9b8a6a9451d5b4431f8da11e24124f2/thoth_test#L764-L772
pexpect - The Blue Book

https://lyz-code.github.io/blue-book/pexpect/
pexpect - The Blue Book

https://lyz-code.github.io/blue-book/pexpect/

python - pexpect send cursor movement - Stack Overflow

https://stackoverflow.com/questions/12981982/pexpect-send-cursor-movement
pexpect - The Blue Book

https://lyz-code.github.io/blue-book/pexpect/
pexpect - The Blue Book

https://lyz-code.github.io/blue-book/pexpect/
GitHub
thoth_test

https://github.com/smorin/thoth/blob/f3aacc45c9b8a6a9451d5b4431f8da11e24124f2/thoth_test#L754-L762
pexpect - The Blue Book

https://lyz-code.github.io/blue-book/pexpect/

python - pexpect send cursor movement - Stack Overflow

https://stackoverflow.com/questions/12981982/pexpect-send-cursor-movement
pexpect - The Blue Book

https://lyz-code.github.io/blue-book/pexpect/
GitHub
thoth_test

https://github.com/smorin/thoth/blob/f3aacc45c9b8a6a9451d5b4431f8da11e24124f2/thoth_test#L730-L738

Unit testing — prompt_toolkit 3.0.38 documentation

https://python-prompt-toolkit.readthedocs.io/en/3.0.38/pages/advanced_topics/unit_testing.html
GitHub
thoth_test

https://github.com/smorin/thoth/blob/f3aacc45c9b8a6a9451d5b4431f8da11e24124f2/thoth_test#L742-L750
GitHub
thoth_test

https://github.com/smorin/thoth/blob/f3aacc45c9b8a6a9451d5b4431f8da11e24124f2/thoth_test#L40-L43
pexpect - The Blue Book

https://lyz-code.github.io/blue-book/pexpect/

python - pexpect send cursor movement - Stack Overflow

https://stackoverflow.com/questions/12981982/pexpect-send-cursor-movement
All Sources