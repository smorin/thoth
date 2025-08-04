Great, I’ll research how to build a CLI-based bordered text box using Prompt Toolkit that supports:

* Prompt input with Shift+Enter multiline editing and up/down arrow history navigation
* Slash command recognition (e.g. `/help`, `/models`, `/provider`) with context-sensitive behavior like print, single-select, or multi-select
* Common Unix-style editing shortcuts
* Modular architecture to allow:

  1. A standalone prototype and tutorial for easy integration
  2. A Thoth-specific version integrated into its CLI ecosystem

I'll provide working prototype code, implementation notes, and guidance on integration with Thoth. I’ll update you once the research is ready.


# Designing an Interactive Prompt Toolkit Input Box for Thoth CLI

## Overview

To build a **pure CLI interactive input** for Thoth, we will leverage the [Python Prompt Toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit) library. Prompt Toolkit provides rich text-based UI components and key handling, allowing us to create a **bordered text input box with multi-line editing, custom key bindings, and dynamic slash commands**. According to the Thoth v2.3 requirements, the interactive mode should include: a bordered input box with multi-line support, slash commands for option configuration, help text above the input, placeholder text, Unix-style shortcuts (e.g. Ctrl+A/E/K), and should exit after submitting one query. We will design an architecture meeting these needs and outline two implementations:

1. **Prototype & Tutorial:** a self-contained example demonstrating the key features (easy to integrate into Thoth).
2. **Thoth-Integrated Version:** tailored to Thoth’s internal commands and workflow (reusing Thoth’s CLI logic).

## Requirements for the Interactive Input Box

Let’s break down the desired features and how Prompt Toolkit can fulfill them:

* **Bordered Text Box:** The input field should be enclosed in a border (with optional title). This improves visual separation from other output.

* **Multi-line Editing:** The user can compose multi-line prompts (e.g. writing a question or code snippet) easily. Common convention (as seen in chat applications like Slack) is **Enter to submit** and **Shift+Enter to insert a newline**.

* **Slash Commands (`/command`):** Typing commands like `/help`, `/models`, `/provider` triggers special behaviors:

  * Some commands produce immediate output (e.g. `/help` should display help text).
  * Others prompt the user to **select an option** (e.g. `/provider` might open a list of providers to choose from, `/models` might let the user pick a model, possibly via multi-select).
  * The interactive UI should handle these commands without exiting the prompt, allowing configuration of options before the final query is submitted.

* **Keyboard Navigation & Shortcuts:**

  * **Arrow Up/Down** should move the cursor through the text box (for editing multi-line text), rather than cycling through history (since the interactive session is single-use).
  * **Common Emacs-like shortcuts**: e.g. **Ctrl+A** (start of line), **Ctrl+E** (end of line), **Ctrl+K** (kill to end of line), etc., should work as expected. Prompt Toolkit’s default key bindings (Emacs mode) cover these.

* **Help/Placeholder Display:** The interface should show usage hints or placeholder text:

  * A help message **above the input box** in a dim style (for example, listing available slash commands or instructions).
  * A **placeholder text** inside the input box when it’s empty (if possible), e.g. “Enter your query…”, which disappears when typing.

* **Single Query Submission:** Once the user finalizes their prompt (and presses Enter to submit), the interactive UI should **exit** and hand off the query to Thoth’s normal execution flow. In other words, the interactive mode is a one-shot composer for a query (not a persistent REPL).

With these in mind, we can design the prompt toolkit layout and behavior.

## Utilizing Prompt Toolkit Features

Prompt Toolkit is well-suited for this task, as it supports multi-line inputs, key binding customization, and even widgets for dialogs/menus. Key features we will use:

* **Prompt Session / Application:** We can use either a high-level `PromptSession` (with `session.prompt()`) or a full `Application` for fine control. A custom Application with a manual layout is needed to create the bordered text box and help text display.
* **Multi-line Input:** Prompt Toolkit allows multi-line editing by setting `multiline=True` on a prompt. By default, when multiline mode is on, the **Enter key inserts a newline** and the user must press `Meta+Enter` (Alt+Enter) or `Esc, Enter` to accept input. We will customize this behavior (see next section).
* **Custom Key Bindings:** We can override or extend key behavior by supplying a `KeyBindings` object. Prompt Toolkit provides default Emacs keybindings (for arrow keys, Ctrl+A/E, etc.) by default. We will add new bindings on top:

  * **Enter vs Shift+Enter:** Our goal is to invert the default multiline behavior: **plain Enter should submit, Shift+Enter should insert newline** (like Slack). This feature was a known request in prompt\_toolkit. We can implement it by capturing the Enter key:

    * Bind `"enter"` to a handler that checks if a Shift key modifier is pressed. If **no Shift**, we will accept the input (finish the prompt).
    * Bind `"s-enter"` (Shift+Enter) to insert a newline character into the buffer. (*Note:* terminals generally do not distinguish Enter vs Shift+Enter as separate key codes, but Prompt Toolkit can treat `S-` as a modifier in key bindings. We may need a workaround if the terminal doesn’t send a distinct code for Shift+Enter. One approach is to use an alternate key like `Alt+Enter` to represent newline, or configure the terminal to send a custom escape sequence for Shift+Enter. For now, we assume Prompt Toolkit can handle `s-enter` as intended.)
    * **Meta+Enter:** We could also allow Alt+Enter as an alternative way to submit or newline. By default, in multiline mode Alt+Enter submits, but since we want Enter to submit, we might repurpose Alt+Enter if needed (or simply leave it).
  * **Arrow Keys:** In multiline context, Up/Down arrow keys normally move the cursor up or down within the text *unless* at the very start/end of the buffer (in which case Prompt Toolkit might cycle history). We will ensure history search is off (or empty history) so that arrow keys strictly navigate the text lines. Using multiline editing mode by itself makes the prompt treat the input as a buffer of lines, so Up/Down will move lines rather than retrieve history.
  * **Other shortcuts:** We will not override standard Emacs keys, so **Ctrl+A, Ctrl+E, Ctrl+K** etc. remain available (Prompt Toolkit’s default Emacs mode provides these behaviors). We’ll run our application in **EditingMode.EMACS** to have these by default (this is the default mode).
* **Layout and Widgets:** For drawing a border and organizing UI components:

  * The **Frame widget** can draw a border around any container. We can wrap our text input area in `Frame(...)` to get a nice border (and even a title if desired). For example: `Frame(TextArea(...), title="Prompt")` would put the TextArea in a bordered box titled “Prompt”.
  * The **TextArea widget** is a multi-line text input field. Unlike `prompt()`, a TextArea used in an Application layout is always multiline (it can contain newlines). We will use `TextArea` for the input field inside the Frame. We can specify an initial `text` (for placeholder) and styling.
  * We can create an **HSplit/VSplit layout**: likely a vertical split (`HSplit`) with the top part for help text and the bottom part for the framed TextArea. For the help text, we can use a non-editable text widget like `Label` or a `Window` displaying formatted text. This help can be static or dynamically updated.
  * Optionally, Prompt Toolkit offers pre-built dialog functions like `input_dialog()` which already create a dialog with a border and text field. However, those are modal popups with OK/Cancel buttons, not exactly our use case. We prefer a custom layout for continuous editing.
* **Running External Code (for slash commands):** Prompt Toolkit allows running code that prints to the terminal **without breaking the UI** via `run_in_terminal()`. This will suspend the prompt rendering, run the given function (we can print output or even invoke Rich console printing), then resume the prompt. We will use this to call Thoth’s existing CLI logic for commands. For example, when the user enters `/models`, we can call Thoth’s `providers_command(..., show_models=True)` which prints a table of models to stdout. Using `run_in_terminal` ensures the output (Rich table in this case) is printed above/outside the prompt cleanly.

## Proposed Architecture & Flow

### 1. UI Layout and Components

We will construct a **full-screen** (or quasi full-screen) Application with a custom layout containing two vertical sections:

* **Help Text Area (Top):** A static or updatable region that provides instructions. For example, it might say: *"Enter your query. Use /help for commands. Shift+Enter for newline, Enter to submit."* in a dim style. We can implement this as a `Window` or `Label` with a text string. We might give it a minimal height or auto-size based on content. If we need it scrollable for lots of help text, we could use `TextArea` in read-only mode, but likely just a few lines of hints is enough.
* **Input Box (Bottom):** A `Frame` containing the `TextArea` for user input. The Frame draws a border around the text box. We can optionally give the frame a title (maybe “Prompt” or nothing). The TextArea inside will be where the user types. We can configure:

  * `height`: a fixed number of lines for the text box (e.g. 5 or 10 lines). If the user’s text exceeds this, the TextArea will scroll. In the earlier example, a height of 10 was used. We might choose a smaller height (since only one query) or let it expand dynamically. (Prompt Toolkit can do dynamic heights, but using a fixed height Frame is simpler). Width will auto-fit or can be set to a percentage of terminal width.
  * `multiline`: The TextArea by nature supports multiline. If using PromptSession instead, we would set `multiline=True`. With a TextArea in an Application, we just allow newlines (no need to set multiline explicitly on TextArea; it’s multiline by default).
  * **Placeholder text:** Prompt Toolkit does not have a built-in placeholder property, but we can simulate one. One way is to pre-populate the TextArea with a dimly styled text like "Enter your query..." and mark it as placeholder. We then add a focus handler or key binding that clears the text on the first keystroke. Alternatively, we simply document the placeholder in the help text above (simpler).
* We will use an `Layout(HSplit([...]))` to stack the help text and input box vertically. This layout is passed to the `Application`. We will set `full_screen=True` for the Application so it controls the whole terminal; this allows nice rendering of the Frame and also lets us capture keys like arrow keys properly. (We could also run it with `full_screen=False` and it will just print the UI in-line, but full\_screen mode is more typical for an interactive editing interface.)

### 2. Key Binding Logic

We create a `KeyBindings` object and add custom handlers:

* **Submit on Enter:** Bind the Enter key to a function that will attempt to submit/exit. In the handler, we will determine if the input content represents a slash command or a final query:

  * If the current text (buffer) starts with `/`, we will **handle a slash command** (see Slash Commands below) instead of exiting.
  * If it’s a normal query (or after finishing slash command handling), we call `event.app.exit(result=buffer_text)`. Exiting the application will break out of the `Application.run()` loop and return control to our code with the entered text as the result.
* **Insert Newline on Shift+Enter:** Bind `s-enter` to insert a newline. In the handler: `event.current_buffer.insert_text("\n")`. By not calling `exit`, the Application remains running and the user sees a new line added in the TextArea. This effectively allows multi-line entry. We must ensure this binding fires **instead of** the default Enter behavior when Shift is held. (If the terminal doesn’t differentiate, another possible binding is using e.g. `Control+O` or some unused key for newline insertion, but the expectation is Shift+Enter).
* **Arrow keys:** We typically don’t need to bind these manually. In multiline mode, the default bindings will move the cursor. We just need to ensure that *history navigation is disabled*. By using a fresh `PromptSession` or not providing a history, the Up arrow won’t fetch previous inputs. In a custom Application, unless we add history handling logic, the arrow keys will just move within the TextArea content. So this should work out of the box.
* **Cancel (Ctrl+C / Ctrl+D):** We should allow the user to abort. Prompt Toolkit’s default will raise a `KeyboardInterrupt` on Ctrl+C if not handled. We can add a binding for `Control-C` and `Control-D` to call `event.app.exit(None)` or so, which would exit the app with no result (and in Thoth’s context, likely just abort the interactive mode). Ensuring a graceful exit on Ctrl+C is important so the terminal isn’t left in an alternate screen state.

We will attach these key bindings to the Application (via `Application(key_bindings=...)`). Prompt Toolkit merges them with default ones so we still have editing/navigation keys.

### 3. Handling Slash Commands

Inside our Enter key handler (or after reading input), we interpret commands starting with `/`. The logic will function as a simple **command parser loop** around the prompt:

* We keep track of some state: e.g. selected provider, selected model, etc., as the user configures options. Initially, state might be default (no specific provider = use all, default mode, etc.).
* When Enter is pressed:

  * Retrieve the input text. If it begins with `/`, do **not exit** the Application yet. Instead, consume that command:

    * **`/help`:** We will display help info. This could be a static message listing available slash commands or even reuse Thoth’s help. Thoth CLI has a help text accessible via `ctx.get_help()` or the `show_*_help()` functions. We might simply print a short custom help for interactive mode (since the commands are different). We can use `run_in_terminal()` to safely print to stdout. For example:

      ```python
      @bindings.add("enter")
      def handle_enter(event):
          text = event.app.current_buffer.text
          if text.strip().startswith("/help"):
              event.app.current_buffer.text = ""  # clear input
              run_in_terminal(lambda: print_help_message())
              return  # do not exit, just return to prompt
          # ... handle other cases ...
      ```

      This will clear the input box and print the help above (once the app resumes, the printed text will remain above the now-empty prompt box). We can similarly call `show_providers_help()` from Thoth for consistency.

    * **`/provider`:** This command likely means the user wants to choose one or multiple providers. There are a couple of ways to implement selection:

      1. **Simple approach (list & type):** On `/provider`, we could list available providers and their status by leveraging `providers_command(show_list=True)`. Thoth’s `providers_command` with `--list` prints a table of providers with a check or X indicating whether they’re configured. We can call this inside `run_in_terminal` to show the table. Then, prompt the user (via the same input box) to enter which provider they want (e.g. the user can type `openai` or `perplexity` as the next input, perhaps with a slash or we could make `/provider openai` in one go). But having them type it defeats the purpose of interactive selection a bit.
      2. **Interactive selection UI:** We can temporarily **suspend the main prompt and open a selection dialog**. Prompt Toolkit’s widgets include `RadioList` (single choice) and `CheckboxList` for multi-choice. We can create a small popup Dialog for provider selection. For example, using `radiolist_dialog(title="Select Provider", values=[("openai","OpenAI"), ...])` which returns the chosen value. Or, implement a custom mini Application with a list of choices and run it modally. This would be more complex but provides a nicer UX. Given time, a simpler method is to do a single-choice: if we assume the user will pick one provider, a radiolist is fine. If we want multi-select (to allow choosing more than one provider for parallel execution), we could use `Checkbox` widgets in a Dialog.

      For clarity, let’s assume single selection (since Thoth’s `--provider` option only takes one, and by default it runs both if not specified). So `/provider` -> user picks one provider to focus on. Implementation:

      ```python
      from prompt_toolkit.shortcuts import radiolist_dialog
      result = radiolist_dialog(
          title="Select Provider",
          text="Choose a provider:",
          values=[("openai","OpenAI"), ("perplexity","Perplexity"), ("mock","Mock")]
      ).run()
      ```

      This will display a bordered dialog with radio options. When `.run()` returns, we get the selected provider key (or None if canceled). We then update our state (e.g. `current_provider = result`) and perhaps update the help/toolbar to show the selection. We also clear the input box so the user can continue.
      We would call this dialog **via** `run_in_terminal()` as well, because it itself is an Application. However, since it’s a prompt\_toolkit dialog, it might need to run within the event loop differently. Alternatively, we simply exit the main Application and restart it after selection. A smoother approach is using an **inline dialog** with Prompt Toolkit’s `Container` system, but that gets complex. Using `run_in_terminal` for a dialog might not work directly (since it wants to take over the UI). In such a case, a safer method is:

      * Exit the main app temporarily when a selection is needed (but we can simulate by pausing, though prompt\_toolkit doesn’t have an official “modal within modal” easy solution).
      * Or do a blocking selection in the key handler by hiding the main UI. Actually, `Application.run()` is blocking; to do a nested prompt, we might need to run the radiolist in a separate thread or prior to launching main loop.

      Simpler: given the complexity, we might implement provider selection by listing options and letting the user type an answer. For example:

      * On `/provider`, use `providers_command(--list)` to show providers with indexes. Then prompt: “Type provider name or number:”. The user then types (in the same input box) the provider keyword (not as a slash command, just as input). We capture that and validate. This is a more manual approach but easier to implement within one application loop.

      For the prototype, we can focus on listing and manual input. In the full integration, we might integrate a better selection UI.

    * **`/models`:** Similar to `/provider`, but shows available models. Likely this depends on the currently selected provider:

      * If a provider is selected (say OpenAI), call `providers_command(show_models=True, filter_provider="openai")`. This will fetch and print a table of model IDs. The user can then pick one model (perhaps by typing its ID or index). Again, we could attempt an interactive scrollable list of models (OpenAI could have many models, but manageable).
      * After choosing, we store the chosen model in state (e.g. `current_model`). We might also automatically set the provider if not already (because model implies provider).

    * Other potential commands: `/mode` (to select the research mode, e.g. default, deep\_dive, etc.), `/project` (to set a project name), etc. “Most common options” likely includes at least mode. We could implement `/mode` with a static list of Thoth modes (perhaps using radiolist as well). For brevity, we’ll focus on provider/model which were explicitly requested.

  In summary, the slash command handling will likely follow a **simple REPL loop**:

  * Keep the Application running after a slash command, output necessary info, update state, clear the input, and prompt again.
  * Only when a non-command input is entered (the actual query) do we break out and proceed to execution.

### 4. Submitting the Query to Thoth

Once the user has configured settings via slash commands and finally enters a prompt (that is not a command), the Application will exit with that text. We then use the collected state (provider, model, mode, etc.) to call Thoth’s internal execution function.

Thoth’s CLI code, when not handling a special subcommand, eventually calls `run_research(mode, query, ...)` to perform the operation. In interactive mode, we should mimic the same. For example:

* Determine the final mode: perhaps default unless user chose one via command (or we could allow them to type the mode as the first word of the query, but that’s ambiguous in interactive context). It might be safer to have a `/mode` command or omit mode selection in the first prototype.
* Use `current_provider` and `current_model` state: If a specific provider was chosen, pass `--provider`. If a specific model was chosen, we might need to tell Thoth to use that model. Thoth CLI doesn’t have a direct `--model` flag; instead, if a provider’s default model is overridden, one way is to create a mode config or use the provider’s own selection mechanism. (Since Thoth’s `create_provider()` likely accepts a config specifying which model if not default). We may have to extend Thoth to accept a model override in interactive mode, or simply set an environment variable for the chosen model (not ideal). For now, assume choosing a model sets the default for that provider (maybe via config).
* Then call `run_research` (or simulate CLI arguments). Essentially, we'd integrate like:

  ```python
  result_text = application.run()  # returns the query string when user hits Enter to submit
  if result_text is None:
      sys.exit(1)  # user aborted
  # Use stored state to set provider/mode options
  final_mode = selected_mode or "default"
  provider_opt = selected_provider  # None means use default multi-provider
  # Possibly set environment or config for model if needed
  asyncio.run(run_research(mode=final_mode, query=result_text, provider=provider_opt, ...))
  ```

  This way, after the interactive prompt, Thoth continues as if the user provided those options via CLI. All the rich output generation and file writing will happen as usual.

### 5. Tutorial Prototype Snippet

Below is a simplified prototype illustrating many of these pieces together. This code can run in isolation to demonstrate the interactive prompt:

```python
from prompt_toolkit import Application, HTML
from prompt_toolkit.layout import Layout, HSplit
from prompt_toolkit.widgets import Frame, TextArea, Label
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.application.current import get_app
from prompt_toolkit.application import run_in_terminal
# State variables
current_provider = None
current_model = None

# Help text to display above the input box
help_text = ("<b>Thoth Interactive Mode</b>\n"
             "Enter your query below. "
             "Use <b>/help</b> for commands, <b>Shift+Enter</b> for newline. "
             "Commands: /provider, /models, /help.\n")

# Create TextArea for input
input_area = TextArea(text="", multiline=True, prompt="❯ ", wrap_lines=True)
input_frame = Frame(input_area, title=" Query ", style="class:input-frame")

# Create a Label (or non-editable TextArea) for help text
help_label = Label(HTML(help_text), style="class:help")

# Assemble layout
layout = Layout(HSplit([help_label, input_frame]))

# Key bindings
bindings = KeyBindings()

@bindings.add("enter")
def _(event):
    """Handle Enter key: submit or process commands."""
    buffer = event.app.current_buffer
    text = buffer.text.strip()
    if text == "":
        return  # ignore empty submit
    if text.startswith("/"):
        # Process slash commands
        cmd, *args = text.split()
        cmd = cmd.lower()
        if cmd == "/help":
            # Print interactive help message
            def print_help():
                print("Slash commands available:\n"
                      "  /help - Show this message\n"
                      "  /provider - Select provider (openai, perplexity, mock)\n"
                      "  /models - List models for current provider and select one\n"
                      "  (Press Ctrl+C to exit interactive mode without submitting.)")
            run_in_terminal(print_help)
        elif cmd == "/provider":
            # List providers and prompt selection
            def list_providers():
                # Imagine this uses Thoth's providers_command(show_list=True)
                print("Available Providers:\n"
                      "1. openai    - OpenAI GPT models\n"
                      "2. perplexity - Perplexity search\n"
                      "3. mock      - Mock (no API key needed)\n")
            run_in_terminal(list_providers)
            # Here, we would prompt user to enter choice. Simplified:
            buffer.text = ""  # clear input for user to type provider
            return  # Don't exit, just clear input and wait for user input
        elif cmd == "/models":
            # Show models for current provider
            prov = current_provider or "openai"
            def list_models():
                print(f"Models for provider '{prov}':")
                # This would call providers_command(show_models=True, filter_provider=prov)
                if prov == "openai":
                    print(" - gpt-4\n - gpt-3.5\n")
                elif prov == "perplexity":
                    print(" - perplexity-advanced\n - perplexity-basic\n")
                else:
                    print(" - mock-model-1\n")
            run_in_terminal(list_models)
            # In a real case, then allow user to type model name to select it
            buffer.text = ""
            return
        else:
            # Unknown command
            run_in_terminal(lambda: print(f"Unknown command: {cmd}"))
        # If we reached here for a known slash command, we likely handled it.
        buffer.text = ""  # clear the input box for further input
        return  # don't exit the app
    else:
        # Not a command, treat as final query submission
        event.app.exit(result=text)

@bindings.add("s-enter")
def _(event):
    """Shift+Enter -> insert newline (soft return)."""
    event.current_buffer.insert_text("\n")

@bindings.add("c-c")
@bindings.add("c-d")
def _(event):
    """Ctrl+C or Ctrl+D -> abort the interactive session."""
    event.app.exit(result=None)

# Create and run the Application
app = Application(layout=layout, key_bindings=bindings, enable_page_navigation_bindings=True,
                  editing_mode='EMACS', mouse_support=False, full_screen=True)
result = app.run()
if result is None:
    print("Interactive session aborted.", file=sys.stderr)
else:
    print(f"Submitting query: {result!r} with provider={current_provider}, model={current_model}")
    # Here we would call run_research(mode, query=result, provider=current_provider, ...) 
```

This prototype demonstrates: a bordered input with a prompt symbol, multi-line input with Shift+Enter, handling of `/help`, `/provider`, `/models` by printing output via `run_in_terminal`, and normal submission on Enter. In a real integration, we would replace the dummy `print` calls with calls into Thoth’s functions (for example, `providers_command`) to display real data. We would also capture user input after listing providers/models to actually set `current_provider`/`current_model` (e.g., if the user types "openai" and presses Enter, we set `current_provider = "openai"` instead of submitting the query). This might involve a small loop or state machine within the key handler.

**Handling multi-step commands:** Notice that for `/provider` and `/models`, the above pseudocode clears the input and returns without exiting – effectively waiting for the user’s next input (e.g., to type the provider name or model). We might detect that as a follow-up response. Another design is to allow commands like `/provider openai` in one go (so the user can directly type the provider name after the command). That would simplify handling: we’d parse `/provider <name>` and set the provider immediately. The same for `/models <model_name>`. This approach avoids needing an extra input round trip. It trades off interactivity for simpler flow. Depending on user preference, either is viable.

### 6. Ensuring Usability and Pitfalls

* **Terminal Compatibility:** As mentioned, distinguishing Shift+Enter may be tricky. If the terminal cannot differentiate, we might choose a different key for newline insertion (e.g. Ctrl+O or Alt+Enter) and inform the user. In many GUI-based terminals, Shift+Enter will just send `\r` like Enter. Prompt Toolkit’s key binding for `s-enter` might not fire in such cases. We should test this in the target environment. The feature request in prompt\_toolkit aimed to allow this Slack-like behavior, so if using the latest version, it may have support or alternative solution. Documentation doesn’t list an explicit “Shift” modifier for Enter, so this could require a workaround. At minimum, Prompt Toolkit does allow **Alt+Enter** by default (Meta+Enter) to accept multiline input, which is the inverse of our goal. We may invert logic: run in multiline mode but bind plain Enter to accept (no modifier) and leave Alt+Enter to insert newline. However, Alt+Enter is not very intuitive to users. We might document both options.
* **Maintaining Default Keybindings:** When adding custom bindings, we ensure not to override essential navigation. In our key handler, we explicitly handle Enter and Shift+Enter. Other keys fall back to default (so arrow keys, backspace, etc. work normally). We set `editing_mode='EMACS'` so that, for example, Ctrl+A jumps to line start and Ctrl+E to line end without extra coding.
* **Styling:** We can style the components (e.g., a dim color for help text, a distinctive border style, etc.) by providing a custom `Style`. For example, define a style class for `.help` text to be dim gray, and `.input-frame` border to a certain color. Prompt Toolkit supports styling via CSS-like classes and `HTML` formatting in text.
* **Placeholder Implementation:** If we want an actual placeholder that disappears on focus, we can implement a focus event. Prompt Toolkit’s `TextArea` could use a `focus` event hook (or we simply initialize with empty text and rely on the help text above as the guide). Another trick is to use the `prompt_continuation` function for multiline prompts to display filler characters or guides for secondary lines (though not exactly placeholder for empty input). Given it’s “implementation-dependent” in PRD, we might choose to skip a complex placeholder and just use the help text to convey what to do.

## Integrating with Thoth’s Architecture

With the prototype validated, integrating into Thoth involves a few adjustments:

* **Embedding in Thoth Codebase:** We likely create an `interactive_mode()` function within the Thoth CLI script (or a separate module). When the `-i/--interactive` flag is passed (detected in Click options), we invoke `interactive_mode()` instead of the normal query execution path. E.g., in the `cli()` function, add:

  ```python
  if interactive_flag: 
      text = interactive_mode()  # runs the Application as described
      if text is None:
          sys.exit(1)  # aborted
      # Use gathered state from interactive_mode (maybe stored globally or returned alongside text)
      # Then call run_research with appropriate parameters
      asyncio.run(run_research(mode=chosen_mode, query=text, provider=chosen_provider, ...))
      return
  ```

  This way, the regular CLI flow is bypassed for interactive. The PRD suggests using `-i/--interactive` to trigger this.

* **Reusing CLI Logic:** We should call existing functions to avoid duplication:

  * Use `providers_command` for listing models or providers instead of our own prints (as long as it prints to `console`, which it does using Rich). We will call it inside `run_in_terminal()` so that its output is displayed while our prompt UI is hidden. For example:

    ```python
    run_in_terminal(lambda: asyncio.run(providers_command(show_list=True)))
    ```

    This prints the providers table. The same for `show_models`:

    ```python
    run_in_terminal(lambda: asyncio.run(providers_command(show_models=True, filter_provider=current_provider)))
    ```

    We must ensure to gather the event loop since `providers_command` is async. Using `asyncio.run` inside `run_in_terminal` is acceptable here (it will execute in a nested fashion).
  * For help text, Thoth’s `show_providers_help()` (and similar for init, status, etc.) print detailed usage. We might have an interactive-specific help, but could also piggyback on these. Perhaps simpler: define our own short help as shown above.
  * We will not re-implement how models are fetched – we rely on `provider.list_models()` inside `providers_command`. This ensures if new providers are added, interactive mode automatically lists them.
  * When the user selects a provider or model, we set the corresponding options. For provider, we can set the `provider` variable that we’ll pass to `run_research` (which corresponds to `--provider` CLI option). For model, since there is no direct `--model` flag, we might have to handle it. One idea: if a model is chosen, we could dynamically create a temporary mode config or adjust the provider’s default model. For example, if provider is "openai" and model "gpt-3.5", we can set `config.data["providers"]["openai"]["model"] = "gpt-3.5"` before running. Or simpler, call `create_provider(name, config)` with an override parameter. This requires minor extension of Thoth’s `create_provider` (not shown in snippet, but likely in the codebase). If minimal changes are desired, we might restrict model selection to providers like OpenAI where the first argument (mode) might be set to a built-in that already has that model (not flexible). A straightforward approach is to let `run_research` pick up the selected model via environment variable or a global. For instance, if current\_provider is "openai" and current\_model is "gpt-4", set `OPENAI_MODEL=gpt-4` env var and modify the OpenAI provider to check that env var. This is a design choice beyond prompt\_toolkit scope but worth noting.

* **Exiting After One Query:** We will design the interactive loop to automatically exit after the user submits one non-command input. If they want to run another query interactively, they would invoke `thoth -i` again. This simplifies state handling (no need to reset the UI for a second query). The PRD explicitly calls for a single-query session.

With these integrations, the second version of the implementation will be specific to Thoth but follow the same pattern as the prototype. All the heavy-lifting (rendering the UI, capturing input, etc.) is handled by Prompt Toolkit, while Thoth’s existing command functions are invoked to maintain consistent behavior. The result is a user-friendly interactive CLI mode where the user can configure common options through intuitive slash commands and compose a multi-line query easily, then let Thoth produce the research output as usual.

## Conclusion

By using Prompt Toolkit’s flexible input handling and Thoth’s built-in command logic, we can create a robust interactive prompt interface that meets the requirements. The **bordered multi-line text box** improves usability for long prompts, **custom key bindings** (Enter vs Shift+Enter) provide a natural editing experience, and **slash commands with dynamic output/selection** expose Thoth’s functionality without requiring the user to recall complex CLI flags. This design will be delivered in two forms: a clear, commented prototype (for tutorial purposes and quick experimentation), and a fully integrated implementation in the Thoth codebase, respecting the architecture and using internal functions wherever possible.

With careful attention to key binding behavior and state management, this interactive mode will make Thoth more accessible and interactive for users crafting complex queries. The approach is validated against Prompt Toolkit’s capabilities and aligns with the planned features in Thoth v2.3, ensuring that we cover all expected features and common pitfalls in implementation.

**Sources:**

* Thoth v2.3 Requirements (Interactive Mode features)
* Prompt Toolkit Documentation – **Multiline input behavior**, **Key binding examples**
* Prompt Toolkit Issue discussions on **Enter vs Shift+Enter** behavior (Slack-like multi-line submit)
* Prompt Toolkit Widgets – **Frame (border) and TextArea** usage
* Thoth CLI Implementation – **Providers listing and model fetching** (for reuse in slash commands)
* Thoth CLI Implementation – **Command help and dispatch logic** (reused for help output and command detection)


Citations
GitHub
thoth.prd.v23.md

https://github.com/smorin/thoth/blob/f3aacc45c9b8a6a9451d5b4431f8da11e24124f2/planning/thoth.prd.v23.md#L15-L23
GitHub
thoth.prd.v23.md

https://github.com/smorin/thoth/blob/f3aacc45c9b8a6a9451d5b4431f8da11e24124f2/planning/thoth.prd.v23.md#L20-L23

Asking for input (prompts) — prompt_toolkit 3.0.50 documentation

https://python-prompt-toolkit.readthedocs.io/en/stable/pages/asking_for_input.html

Asking for input (prompts) — prompt_toolkit 3.0.50 documentation

https://python-prompt-toolkit.readthedocs.io/en/stable/pages/asking_for_input.html

Asking for input (prompts) — prompt_toolkit 3.0.50 documentation

https://python-prompt-toolkit.readthedocs.io/en/stable/pages/asking_for_input.html

Allow Shift+Enter/Return-only for multiline mode · Issue #451 · prompt-toolkit/python-prompt-toolkit · GitHub

https://github.com/prompt-toolkit/python-prompt-toolkit/issues/451

Is it possible to have a "shift + enter" keybinding? · Issue #529 - GitHub

https://github.com/jonathanslenders/python-prompt-toolkit/issues/529

Asking for input (prompts) — prompt_toolkit 3.0.50 documentation

https://python-prompt-toolkit.readthedocs.io/en/stable/pages/asking_for_input.html
prompttoolkit Documentation

https://media.readthedocs.org/pdf/python-prompt-toolkit/stable/python-prompt-toolkit.pdf
prompttoolkit Documentation

https://media.readthedocs.org/pdf/python-prompt-toolkit/stable/python-prompt-toolkit.pdf

Asking for input (prompts) — prompt_toolkit 3.0.50 documentation

https://python-prompt-toolkit.readthedocs.io/en/stable/pages/asking_for_input.html
GitHub
thoth

https://github.com/smorin/thoth/blob/f3aacc45c9b8a6a9451d5b4431f8da11e24124f2/thoth#L1929-L1938
GitHub
thoth

https://github.com/smorin/thoth/blob/f3aacc45c9b8a6a9451d5b4431f8da11e24124f2/thoth#L1947-L1955

Draw Frame in non full-screen mode · Issue #730 · prompt-toolkit/python-prompt-toolkit · GitHub

https://github.com/prompt-toolkit/python-prompt-toolkit/issues/730

Draw Frame in non full-screen mode · Issue #730 · prompt-toolkit/python-prompt-toolkit · GitHub

https://github.com/prompt-toolkit/python-prompt-toolkit/issues/730

Draw Frame in non full-screen mode · Issue #730 · prompt-toolkit/python-prompt-toolkit · GitHub

https://github.com/prompt-toolkit/python-prompt-toolkit/issues/730

Asking for input (prompts) — prompt_toolkit 3.0.50 documentation

https://python-prompt-toolkit.readthedocs.io/en/stable/pages/asking_for_input.html
GitHub
thoth

https://github.com/smorin/thoth/blob/f3aacc45c9b8a6a9451d5b4431f8da11e24124f2/thoth#L536-L545
GitHub
thoth

https://github.com/smorin/thoth/blob/f3aacc45c9b8a6a9451d5b4431f8da11e24124f2/thoth#L718-L727
GitHub
thoth

https://github.com/smorin/thoth/blob/f3aacc45c9b8a6a9451d5b4431f8da11e24124f2/thoth#L536-L544
GitHub
thoth

https://github.com/smorin/thoth/blob/f3aacc45c9b8a6a9451d5b4431f8da11e24124f2/thoth#L1866-L1875
GitHub
thoth

https://github.com/smorin/thoth/blob/f3aacc45c9b8a6a9451d5b4431f8da11e24124f2/thoth#L1876-L1884

Reference — prompt_toolkit 3.0.50 documentation

https://python-prompt-toolkit.readthedocs.io/en/stable/pages/reference.html
GitHub
thoth

https://github.com/smorin/thoth/blob/f3aacc45c9b8a6a9451d5b4431f8da11e24124f2/thoth#L1948-L1956
GitHub
thoth

https://github.com/smorin/thoth/blob/f3aacc45c9b8a6a9451d5b4431f8da11e24124f2/thoth#L622-L632
GitHub
thoth

https://github.com/smorin/thoth/blob/f3aacc45c9b8a6a9451d5b4431f8da11e24124f2/thoth#L630-L639

Asking for input (prompts) — prompt_toolkit 3.0.50 documentation

https://python-prompt-toolkit.readthedocs.io/en/stable/pages/asking_for_input.html

Asking for input (prompts) — prompt_toolkit 3.0.50 documentation

https://python-prompt-toolkit.readthedocs.io/en/stable/pages/asking_for_input.html

Asking for input (prompts) — prompt_toolkit 3.0.50 documentation

https://python-prompt-toolkit.readthedocs.io/en/stable/pages/asking_for_input.html
GitHub
thoth.prd.v23.md

https://github.com/smorin/thoth/blob/f3aacc45c9b8a6a9451d5b4431f8da11e24124f2/planning/thoth.prd.v23.md#L19-L22
GitHub
thoth.prd.v23.md

https://github.com/smorin/thoth/blob/f3aacc45c9b8a6a9451d5b4431f8da11e24124f2/planning/thoth.prd.v23.md#L15-L19
GitHub
thoth

https://github.com/smorin/thoth/blob/f3aacc45c9b8a6a9451d5b4431f8da11e24124f2/thoth#L1866-L1874
GitHub
thoth.prd.v23.md

https://github.com/smorin/thoth/blob/f3aacc45c9b8a6a9451d5b4431f8da11e24124f2/planning/thoth.prd.v23.md#L22-L24

Asking for input (prompts) — prompt_toolkit 3.0.50 documentation

https://python-prompt-toolkit.readthedocs.io/en/stable/pages/asking_for_input.html
GitHub
thoth

https://github.com/smorin/thoth/blob/f3aacc45c9b8a6a9451d5b4431f8da11e24124f2/thoth#L496-L505
All Sources